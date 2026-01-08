#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
import asyncio
import time
import json
import html
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
import random
import feedparser
import httpx
import re
import urllib3
# Suppress InsecureRequestWarning for cleaner logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import socket
import ssl
# Set a global timeout for all socket operations
socket.setdefaulttimeout(30)

logger = logging.getLogger(__name__)

# GLOBAL SSL PATCh: Allow Legacy Renegotiation
try:
    _ctx = ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE
    if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
         _ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    else:
         _ctx.options |= 0x4
    
    try:
        _ctx.options |= getattr(ssl, "OP_legacy_server_connect", 0x4)
        if hasattr(_ctx, 'set_ciphers'):
            _ctx.set_ciphers('DEFAULT@SECLEVEL=1')
    except Exception:
        pass
    ssl._create_default_https_context = lambda: _ctx
except Exception as e:
    logger.warning(f"Failed to apply SSL patch: {e}")

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    BeautifulSoup = None
    _HAS_BS4 = False

from sqlalchemy.orm import Session
from .settings import settings
from .database import SessionLocal, engine, Base
from .models import Article, Blacklist, CrawlerStatus
from .sources import SOURCES, build_gnews_rss, CONFIG
from . import nlp
from .dedup import find_duplicate_article, get_article_hash, normalize_url
from .event_matcher import upsert_event_for_article
from .html_scraper import HTMLScraper, fetch_article_full_text_async, extract_metadata

Base.metadata.create_all(bind=engine)

# User Requirement: Skip any news before 2025-01-01
CRAWL_MIN_DATE = datetime(2025, 1, 1)

# Optional classifier loader (joblib) - Removed as it was unused and causing import overhead
_classifier = None


def _get_impact_value(impact_data):
    if impact_data is None:
        return None
    if isinstance(impact_data, (int, float)):
        return impact_data
    if isinstance(impact_data, dict):
        return impact_data.get("num") or impact_data.get("value")
    if isinstance(impact_data, list):
        nums = []
        for x in impact_data:
            if isinstance(x, (int, float)): nums.append(x)
            elif isinstance(x, dict): nums.append(x.get("num") or x.get("value") or 0)
        return max(nums) if nums else None
    return impact_data


def _to_dt(entry) -> datetime:
    tt = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if tt:
        # Ensure UTC timezone handling is robust
        return datetime(*tt[:6], tzinfo=timezone.utc).astimezone(timezone.utc).replace(tzinfo=None)
    
    # Try different date fields if parsed struct is missing
    if hasattr(entry, "published"):
        from dateutil import parser as date_parser
        try:
            dt = date_parser.parse(entry.published)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            pass

    return datetime.now(timezone.utc)

def _extract_image_url(entry, soup=None, base_url=None) -> str | None:
    """Extract best image URL from Feed Entry or HTML Soup."""
    # 1. Check RSS media extensions (Media RSS)
    if entry:
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0]['url']
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0]['url']
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').startswith('image/') or link.get('rel') == 'enclosure':
                    return link['href']
        
        # Check description for img tag
        try:
            desc = getattr(entry, "summary", "") or getattr(entry, "description", "")
            if desc and "<img" in desc:
                # specific regex for src
                m = re.search(r'src=["\']([^"\']+)["\']', desc)
                if m:
                    return m.group(1)
        except Exception:
            pass

    # 2. Check HTML soup (standardized metadata extraction)
    if soup:
        meta = extract_metadata(soup)
        if meta["image"]:
            return meta["image"]
            
        # 3. Fallback: Find the first significant image in the body
        # Ignore common logos, icons, and small social buttons
        from urllib.parse import urljoin
        
        images = soup.find_all("img")
        for img in images:
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if not src: continue
            
            # Resolve relative URLs
            if base_url: src = urljoin(base_url, src)
            
            # [OPTIMIZATION] Junk image filtering logic
            low_src = src.lower()
            junk_found = any(p in low_src for p in ["logo", "icon", "avatar", "social", "banner", "btn", "loading", "placeholder", "fallback", "default"])
            if junk_found: continue
            
            # Skip common static assets
            if any(low_src.endswith(ext) for ext in [".svg", ".gif"]): continue

            # Try to check attributes that suggest size
            width = img.get("width")
            height = img.get("height")
            try:
                if width and int(width) < 100: continue
                if height and int(height) < 100: continue
            except ValueError:
                pass
                
            return src

    return None

# Feed state file to persist ETag / Last-Modified per feed URL
FEED_STATE_FILE = Path(__file__).resolve().parents[1] / "data" / "feed_state.json"


def _load_feed_state() -> dict:
    try:
        if FEED_STATE_FILE.exists():
            with FEED_STATE_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_feed_state(state: dict) -> None:
    try:
        FEED_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with FEED_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


async def _fetch_all_feeds(feed_urls: list[str], headers: dict, timeout_seconds: int, force_update: bool = False) -> dict:
    """Fetch all feeds concurrently with conditional requests (ETag / If-Modified-Since).
    
    Includes User-Agent rotation and retries (3 attempts).
    Returns mapping url -> dict(text/elapsed,error,not_modified,status_code).
    """
    results: dict = {}
    # Increased limits and shorter timeouts for faster cycle
    timeout = httpx.Timeout(timeout_seconds, connect=10.0, read=20.0)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    
    # Default headers for feed fetching
    default_headers = {
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
    }
    headers = {**default_headers, **headers}

    # load persisted feed state for ETag/Last-Modified
    feed_state = _load_feed_state()

    # Allow insecure SSL (verify=False) to support gov sites with bad certs
    transport = httpx.AsyncHTTPTransport(retries=3, verify=False)
    
    # Proxy rotation logic
    client_kwargs = {
        "timeout": timeout,
        "follow_redirects": True,
        "limits": limits,
        "transport": transport
    }
    
    if settings.crawler_proxies:
        proxy_url = random.choice(settings.crawler_proxies)
        client_kwargs["proxy"] = proxy_url
        logger.debug(f"Using proxy for feed crawl: {proxy_url}")

    async with httpx.AsyncClient(**client_kwargs) as client:
        tasks = {}
        for url in feed_urls:
            async def _get(u=url):
                # INNER JITTER: Sleep for 0.5 - 3.0 seconds to avoid slamming servers at once
                await asyncio.sleep(random.uniform(0.5, 3.0))
                
                start = time.perf_counter()
                
                # Retry loop
                for attempt in range(3):
                    try:
                        # Rotate User-Agent
                        current_ua = random.choice(settings.user_agents)
                        local_headers = {**headers, "User-Agent": current_ua}
                        
                        state = feed_state.get(u, {})
                        if not force_update:
                            if state.get("etag"):
                                local_headers["If-None-Match"] = state.get("etag")
                            if state.get("last_modified"):
                                local_headers["If-Modified-Since"] = state.get("last_modified")

                        # [OPTIMIZATION] If multiple proxies exist, pick a new one per retry or per URL
                        # to avoid being stuck on a bad node.
                        current_client = client
                        close_client = False
                        
                        if settings.crawler_proxies and len(settings.crawler_proxies) > 1:
                            # Use a separate client for this request to use a specific proxy
                            new_proxy = random.choice(settings.crawler_proxies)
                            current_client = httpx.AsyncClient(
                                proxy=new_proxy, 
                                timeout=timeout, 
                                follow_redirects=True, 
                                verify=False,
                                transport=httpx.AsyncHTTPTransport(retries=0) # We handle retries manually
                            )
                            close_client = True
                        
                        try:
                            r = await current_client.get(u, headers=local_headers)
                            elapsed = time.perf_counter() - start

                            # handle 304 Not Modified
                            if r.status_code == 304:
                                return (u, {"not_modified": True, "elapsed": elapsed, "status_code": 304})

                            r.raise_for_status() # successful or raise error

                            # successful fetch, update state
                            try:
                                h = {}
                                if r.headers.get("etag"):
                                    h["etag"] = r.headers.get("etag")
                                if r.headers.get("last-modified"):
                                    h["last_modified"] = r.headers.get("last-modified")
                                if h:
                                    feed_state[u] = {**feed_state.get(u, {}), **h, "fetched_at": datetime.now(timezone.utc).isoformat()}
                            except Exception:
                                pass

                            return (u, {"text": r.text, "elapsed": elapsed, "status_code": r.status_code})
                        finally:
                            if close_client:
                                await current_client.aclose()
                        
                    except httpx.HTTPError as e:
                        # if last attempt, return error
                        if attempt == 2:
                            elapsed = time.perf_counter() - start
                            return (u, {"error": str(e), "elapsed": elapsed})
                        # otherwise wait briefly and retry
                        await asyncio.sleep(1 * (attempt + 1))
                    except Exception as e:
                         # Non-HTTP errors (e.g. specialized logic), return immediately
                        elapsed = time.perf_counter() - start
                        return (u, {"error": str(e), "elapsed": elapsed})

            tasks[url] = asyncio.create_task(_get())

        for u, t in tasks.items():
            u_ret, data = await t
            results[u_ret] = data

    # Batch save state at the end to prevent I/O blocking in the loop
    if feed_state:
        _save_feed_state(feed_state)

    return results

async def _ingest_article_async(db: Session, src, title: str, link: str, published_at: datetime, summary_raw: str) -> tuple[Article | None, str]:
    """
    Centralized logic to process, classify, and save an article.
    Handles deduplication, status upgrades (Pending -> Approved), and blacklisting.
    """
    article_hash = get_article_hash(title, src.domain)
    
    # 0. Blacklist Check
    if db.query(Blacklist).filter(Blacklist.news_hash == article_hash).first():
        return None, "blacklisted"

    # 1. Deduplication (Same-Source)
    existing = await asyncio.to_thread(find_duplicate_article, db, src.domain, link, title, published_at)
    
    if existing and existing.status == "approved":
        return None, "duplicate-approved"

    # 2. NLP Diagnosis
    diag = await asyncio.to_thread(nlp.diagnose, f"{title}\n{summary_raw}", title=title, authority_level=src.authority_level)
    score = diag["score"]
    
    if existing:
        # Upgrade Pending -> Approved if new score is high enough
        if existing.status == "pending" and score >= 15.0:
            existing.status = "approved"
            existing.score = score
            # Update meta if it's better now
            meta = await asyncio.to_thread(nlp.extract_all_metadata, summary_raw, summary_raw, title, existing_signals=diag["signals"])
            # [REFACTOR] Event upsert moved to main loop after content check
            _log_to_review_file(src, title, link, published_at, score, diag["reason"], "upgraded_to_approved")
            return existing, "upgraded"
            
        return None, "duplicate-pending"

    # 2. Status Assignment
    status = "auto-blacklisted"
    
    # [FIX] Respect NLP Vetoes
    is_vetoed = diag["signals"].get("absolute_veto", False) or \
                (diag["signals"].get("conditional_veto", False) and diag["signals"].get("hazard_score", 0) == 0)
    
    if not is_vetoed:
        # [STRATEGY v5] Professional Grade Thresholds
        # 1. Strong titles (disaster words/VIP) approve faster.
        # 2. Raised pending floor to 11.5 to ensure >90% probability for humans.
        is_strong_title = diag["signals"].get("is_vip", False) or nlp.title_contains_disaster_keyword(title)
        
        # Confirmation of core signals
        has_hazard = diag["signals"].get("hazard_score", 0) > 0
        has_impact = diag["signals"].get("impact_hits", False)
        has_casualties = diag["signals"].get("impact_details", {}).get("deaths") or diag["signals"].get("impact_details", {}).get("missing")
        
        approval_threshold = 14.5 if is_strong_title else 17.0
        
        # Fast-track for articles with casualties and a confirmed hazard match
        if has_casualties and has_hazard and score >= 13.5:
            status = "approved"
        elif score >= approval_threshold:
            # [CRITICAL] Require hazard match (rule) or VIP term for auto-approve
            if has_hazard or diag["signals"].get("is_vip", False):
                status = "approved"
            else:
                status = "pending"
        elif score >= 11.5:
            status = "pending"

    if status == "auto-blacklisted":
        if not db.query(Blacklist).filter(Blacklist.news_hash == article_hash).first():
            db.add(Blacklist(news_hash=article_hash, title=title, reason=f"Low Score: {score:.1f}"))
        
        if score >= 3.0 or diag["signals"].get("rule_matches"):
            _log_to_review_file(src, title, link, published_at, score, diag["reason"], "auto_blacklisted", diag["signals"])
        return None, status

    # 3. Full Ingestion
    meta = await asyncio.to_thread(nlp.extract_all_metadata, summary_raw, summary_raw, title, existing_signals=diag["signals"])

    article = Article(
        source=src.name, domain=src.domain, title=title, url=link,
        published_at=published_at, news_hash=article_hash,
        status=status, score=score,
        disaster_type=meta["disaster_type"],
        province=meta["province"],
        summary=meta["summary"],
        stage=meta["stage"],
        needs_verification=meta["needs_verification"],
        deaths=_get_impact_value(meta["impacts"]["deaths"]),
        missing=_get_impact_value(meta["impacts"]["missing"]),
        injured=_get_impact_value(meta["impacts"]["injured"]),
        damage_billion_vnd=_get_impact_value(meta["impacts"]["damage_billion_vnd"]),
        impact_details=meta["impact_details"],
        commune=meta["impacts"].get("commune"),
        village=meta["impacts"].get("village"),
        route=meta["impacts"].get("route"),
        landmark=meta["landmark"],
        cause=meta["impacts"].get("cause"),
        characteristics=meta["impacts"].get("characteristics"),
        agency=meta["impacts"].get("agency")[:255] if meta["impacts"].get("agency") else None
    )

    if status in ["approved", "pending"]:
        log_action = "auto_approved" if status == "approved" else "pending_review"
        _log_to_review_file(src, title, link, published_at, score, diag["reason"], log_action)

    try:
        db.add(article)
        db.flush()
        # [REFACTOR] Event upsert moved to main loop after content check
        # Commit will be handled by the caller in batches for better performance
        return article, status
    except Exception as e:
        db.rollback()
        logger.error(f"   [ERROR_INGEST] {src.name}: {e}")
        return None, "error"

def _log_to_review_file(src, title, link, published_at, score, reason, action, signals=None):
    try:
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "published_at": published_at.isoformat(),
            "action": action,
            "source": src.name,
            "domain": src.domain,
            "title": title,
            "url": link,
            "score": score,
            "reason": reason
        }
        if signals: record["diagnose"] = signals
        with open(logs_dir / "review_potential_disasters.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception: pass

async def _process_once_async(force_update: bool = False, only_sources: list[str] = None) -> dict:
    """Async implementation of a single crawl run."""
    db: Session = SessionLocal()
    new_count = 0
    start_total = time.perf_counter()
    per_source_stats = []
    
    try:
        sources_to_process = [s for s in SOURCES if not only_sources or s.name in only_sources]
        sources_info: dict = {}
        all_feed_urls = []

        for src in sources_to_process:
            feeds = [("primary", src.primary_rss), ("backup", src.backup_rss)]
            feeds = [(t, u) for t, u in feeds if u]
            feeds.append(("gnews", build_gnews_rss(src.domain, context_terms=CONFIG.get("gnews_context_terms", []))))
            
            sources_info[src.name] = {"source": src, "feeds": feeds, "added": 0}
            all_feed_urls.extend([url for _, url in feeds])

        headers = {"User-Agent": settings.user_agent}
        fetched = await _fetch_all_feeds(all_feed_urls, headers, settings.request_timeout_seconds, force_update=force_update)

        for name, info in sources_info.items():
            src = info["source"]
            stat = {"source": name, "feed_used": [], "elapsed": 0.0, "error": None, "articles_added": 0}
            feed_worked = False

            for f_type, f_url in info["feeds"]:
                f_data = fetched.get(f_url)
                if not f_data or f_data.get("error"): continue
                
                stat["elapsed"] += f_data.get("elapsed", 0.0)
                if f_data.get("not_modified"):
                    feed_worked = True
                    stat["feed_used"].append(f_type)
                    continue

                # [OPTIMIZATION] Run feedparser in executor to avoid blocking the event loop
                parsed_feed = await asyncio.get_event_loop().run_in_executor(
                    None, feedparser.parse, f_data.get("text", "")
                )
                feed = entry_list = parsed_feed.entries
                if not entry_list: continue
                
                feed_worked = True
                stat["feed_used"].append(f_type)
                
                for entry in entry_list[:(50 if f_type == "gnews" else 200)]:
                    title = html.unescape(html.unescape(getattr(entry, "title", ""))).strip()
                    title = re.sub(r"\s+", " ", title)
                    link = getattr(entry, "link", "").strip()
                    pub_at = _to_dt(entry)
                    if pub_at < CRAWL_MIN_DATE: continue

                    raw_sum = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                    sum_raw = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(html.unescape(raw_sum)))).strip()
                    
                    article, status = await _ingest_article_async(db, src, title, link, pub_at, sum_raw)
                    if article:
                        await _enrich_article_async(db, src, article)
                        
                        # [FIX] Check for empty content (ghost article prevention)
                        has_content = (article.summary and len(article.summary.strip()) > 10) or \
                                      (article.full_text and len(article.full_text.strip()) > 50)
                                      
                        if not has_content:
                            logger.warning(f"   [SKIPPING] Empty content: {title[:50]}...")
                            db.delete(article)
                        else:
                            new_count += 1
                            info["added"] += 1
                            _log_artic_status(src.name, title, status, article.score)
                            
                            # Late binding of event to ensure we don't create ghost events for empty articles
                            await asyncio.to_thread(upsert_event_for_article, db, article)

                if feed_worked: break

            force_html = any(x in src.domain for x in ["thoitietvietnam", "nchmf", "kttv"])
            if not feed_worked or force_html:
                try:
                    scraped = await HTMLScraper(timeout=settings.request_timeout_seconds).scrape_source(src.domain)
                    if scraped:
                        stat["feed_used"].append("html_scraper")
                        feed_worked = True
                        for item in scraped[:50]:
                            a, s = await _ingest_article_async(db, src, item["title"], item["url"], datetime.now(timezone.utc), item.get("summary", ""))
                            if a:
                                await _enrich_article_async(db, src, a)
                                
                                # [FIX] Check content
                                has_content = (a.summary and len(a.summary.strip()) > 10) or \
                                              (a.full_text and len(a.full_text.strip()) > 50)
                                if not has_content:
                                    logger.warning(f"   [SKIPPING] Empty content (scraped): {item['title'][:50]}...")
                                    db.delete(a)
                                else:
                                    new_count += 1
                                    info["added"] += 1
                                    _log_artic_status(src.name, item["title"], s, a.score)
                                    await asyncio.to_thread(upsert_event_for_article, db, a)
                except Exception as e:
                    stat["error"] = f"scraper error: {str(e)[:50]}"

            if not feed_worked: stat["error"] = "all sources failed"
            stat["articles_added"] = info["added"]
            stat["feed_used"] = ", ".join(stat["feed_used"])
            per_source_stats.append(stat)
            
            # Batch Commit per Source
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                stat["error"] = f"Commit failed: {e}"
                logger.error(f"Commit failed for {name}: {e}")

            _update_source_status(db, name, stat)

        await _finalize_crawl(db, new_count, start_total, per_source_stats)
        return {"status": "success", "new_articles": new_count, "sources_processed": len(per_source_stats)}

    except Exception as e:
        logger.critical(f"[CRITICAL] crawler cycle failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

def _log_artic_status(src_name, title, status, score):
    tag = f"[{status.upper()}]"
    # [OPTIMIZATION] Reduce log spam in production
    if status == "approved":
        logger.info(f"   {tag} {src_name}: {title[:70]}... (Score: {score:.1f})")
    else:
        logger.debug(f"   {tag} {src_name}: {title[:70]}... (Score: {score:.1f})")

async def _enrich_article_async(db: Session, src, article):
    """Enrich article with full-text content and better metadata."""
    should_fetch = src.trusted or nlp.title_contains_disaster_keyword(article.title)
    if not should_fetch:
        for data in nlp.IMPACT_KEYWORDS.values():
            if any(kw.lower() in (article.title + (article.summary or "")).lower() for kw in data.get("terms", [])):
                should_fetch = True; break
    
    if not should_fetch: return

    try:
        res = await fetch_article_full_text_async(article.url, timeout=settings.request_timeout_seconds)
        if res and res.get("text"):
            txt = res["text"]
            article.full_text = txt[:100000]
            if res.get("images") and not article.image_url:
                article.image_url = res["images"][0]
            
            # [FIX] Attempt to correct publication date from body text or metadata
            real_date = nlp.extract_publication_date_from_text(txt[:2000])
            scraper_meta = res.get("meta") or {}
            if not real_date and scraper_meta.get("published_time"):
                from dateutil import parser as date_parser
                try:
                    dt = date_parser.parse(scraper_meta["published_time"])
                    if dt.tzinfo: dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    real_date = dt
                except Exception: pass
            
            if real_date:
                # Sanity check: valid date and not in future
                if real_date < datetime.now(timezone.utc) + timedelta(days=1):
                    # Update if difference is significant (> 1 hour)
                    if abs((article.published_at - real_date).total_seconds()) > 3600:
                        # logger.info(f"   [DATE_FIX] {article.title[:30]}... updated date to {real_date}")
                        article.published_at = real_date

            meta = await asyncio.to_thread(nlp.extract_all_metadata, txt, article.summary or "", article.title)
            
            for f in ["deaths", "missing", "injured", "damage_billion_vnd"]:
                val = _get_impact_value(meta["impacts"].get(f))
                if val is not None:
                    current_val = getattr(article, f) or 0
                    # Update if new value is better (higher) or current is 0
                    if val > current_val or (current_val == 0 and val > 0):
                        setattr(article, f, val)
            
            for lf in ["province", "commune", "village", "route", "cause"]:
                new_val = meta.get(lf) if lf == "province" else meta["impacts"].get(lf)
                if new_val and new_val != "unknown" and (not getattr(article, lf) or getattr(article, lf) == "unknown"):
                    setattr(article, lf, new_val)
            
            if meta.get("needs_verification"): article.needs_verification = True
            
            upsert_event_for_article(db, article)
            db.flush()
    except Exception: pass

def _update_source_status(db: Session, name, stat):
    try:
        c = db.query(CrawlerStatus).filter(CrawlerStatus.source_name == name).first()
        if not c:
            c = CrawlerStatus(source_name=name); db.add(c)
        c.last_run_at = datetime.now(timezone.utc)
        c.articles_added = stat["articles_added"]
        c.latency_ms = int(stat["elapsed"] * 1000)
        c.feed_used = stat["feed_used"]
        if stat["error"]:
            c.status, c.last_error = "error", stat["error"]
        elif "gnews" in stat["feed_used"] and "primary" not in stat["feed_used"]:
            c.status, c.last_error = "warning", "Using GNews fallback"
        else:
            c.status, c.last_error = "success", None
        db.commit()
    except Exception: db.rollback()

async def _finalize_crawl(db, new_count, start_time, per_source):
    total_elapsed = time.perf_counter() - start_time
    logger.info(f"[INFO] crawl finished - new={new_count} - time={total_elapsed:.2f}s")
    
    try:
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "new_articles": new_count, "elapsed": total_elapsed, "per_source": per_source}
        with open(logs_dir / "crawl_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception: pass

    if new_count > 0:
        try:
            from .cache import cache
            cache.delete_match("stats_*"); cache.delete_match("articles_latest_*"); cache.delete_match("ev_*")
            from . import broadcast
            broadcast.publish_event_sync({"type": "update", "message": f"Found {new_count} new articles"})
        except Exception: pass

def process_once(force: bool = False, only_sources: list[str] = None) -> dict:
    return asyncio.run(_process_once_async(force_update=force, only_sources=only_sources))

def cleanup_old_pending_articles():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        deleted = db.query(Article).filter(Article.status == "pending", Article.published_at < cutoff).delete(synchronize_session=False)
        db.commit()
        if deleted > 0: logger.info(f"Cleaned up {deleted} old pending articles.")
    except Exception as e:
        db.rollback(); logger.error(f"Failed to cleanup old pending articles: {e}")
    finally: db.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.once:
        import pprint; pprint.pprint(process_once(force=args.force))
    else: logger.info("Use --once; scheduling is handled by backend server.")

if __name__ == "__main__":
    main()
