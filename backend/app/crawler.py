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
from .event_matcher import upsert_event_for_article, emit_event_notifications
from .html_scraper import HTMLScraper, fetch_article_full_text_async, extract_metadata
from .cache import cache

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

    return datetime.now(timezone.utc).replace(tzinfo=None)

def _extract_image_url(entry, soup=None, base_url=None) -> str | None:
    """Extract best image URL from Feed Entry or HTML Soup."""
    # 1. Check RSS media extensions (Media RSS)
    raw_img = None
    if entry:
        if hasattr(entry, 'media_content') and entry.media_content:
            raw_img = entry.media_content[0]['url']
        elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            raw_img = entry.media_thumbnail[0]['url']
        elif hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').startswith('image/') or link.get('rel') == 'enclosure':
                    raw_img = link['href']
                    break
        
        # Check description for img tag if still no image
        if not raw_img:
            try:
                desc = getattr(entry, "summary", "") or getattr(entry, "description", "")
                if desc and "<img" in desc:
                    m = re.search(r'src=["\']([^"\']+)["\']', desc)
                    if m: raw_img = m.group(1)
            except Exception: pass

    # 2. Check HTML soup (standardized metadata extraction)
    if not raw_img and soup:
        meta = extract_metadata(soup)
        if meta["image"]:
            raw_img = meta["image"]

    # Filter junk from RSS/Meta results
    if raw_img:
        low_img = raw_img.lower()
        is_junk = any(p in low_img for p in ["logo", "icon", "avatar", "social", "banner", "btn", "loading", "placeholder", "fallback", "default"])
        if is_junk: raw_img = None
        else: return raw_img # FOUND GOOD IMAGE
            
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
                    temp_client = None
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

                        # [OPTIMIZATION] Scalable Proxy Logic
                        # Attempt 0: Use default client (shared pool) -> Efficient
                        # Attempt 1+: If we have proxies, spawn a temp client to rotate IP -> Robust
                        active_client = client
                        
                        should_rotate_proxy = (attempt > 0) and settings.crawler_proxies and len(settings.crawler_proxies) > 1
                        
                        if should_rotate_proxy:
                            # Create a temporary single-use client for this retry
                            new_proxy = random.choice(settings.crawler_proxies)
                            temp_client = httpx.AsyncClient(
                                proxy=new_proxy, 
                                timeout=timeout, 
                                follow_redirects=True, 
                                verify=False,
                                transport=httpx.AsyncHTTPTransport(retries=0)
                            )
                            active_client = temp_client
                        
                        try:
                            # Perform Request
                            r = await active_client.get(u, headers=local_headers)
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
                            # Only close the temp client if we created one
                            if temp_client:
                                await temp_client.aclose()
                        
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
    
    # 0. Junk / Landing Page Check (Skip without blacklisting)
    if nlp.is_junk_title(title):
        return None, "junk-ignored"

    # 0.1 Title Relevance Check (Strict User Request)
    # Article title MUST contain a disaster keyword or be a critical action/VIP term.
    # This filters out high-scoring but irrelevant news (e.g. financial reports with "billion VND").
    if not nlp.title_contains_disaster_keyword(title):
        return None, "ignored-title-weak"
    
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
        # [FEATURE] Allow re-enrichment if very recent (<12h) and impact is missing
        # Many news sites update the SAME URL with death/damage counts later.
        pub_at_utc = existing.published_at.replace(tzinfo=None)
        age_hours = (datetime.now(timezone.utc).replace(tzinfo=None) - pub_at_utc).total_seconds() / 3600.0
        if age_hours < 12.0 and score >= 10.0 and \
           not any([existing.deaths, existing.missing, existing.injured, existing.damage_billion_vnd]):
            return existing, "upgradable-metrics"

        # Upgrade Pending -> Approved if new score is high enough
        if existing.status == "pending" and score >= 15.0:
            existing.status = "approved"
            existing.score = score
            # Update meta if it's better now
            meta = await asyncio.to_thread(nlp.extract_all_metadata, summary_raw, summary_raw, title, existing_signals=diag["signals"])
            _log_to_review_file(src, title, link, published_at, score, diag["reason"], "upgraded_to_approved")
            return existing, "upgraded"
            
        return None, "duplicate-pending"

    # 2. Status Assignment
    status = "auto-blacklisted"
    
    # [FIX] Respect NLP Vetoes
    is_vetoed = diag["signals"].get("absolute_veto", False) or \
                (diag["signals"].get("conditional_veto", False) and diag["signals"].get("hazard_score", 0) == 0)
    
    if not is_vetoed:
        # [STRATEGY v6] Standardized Thresholds via SCORING_WEIGHTS
        from .sources import SCORING_WEIGHTS as CONF
        
        # 1. Strong titles (disaster words/VIP) approve faster.
        is_strong_title = diag["signals"].get("is_vip", False) or \
                          (nlp.HIGH_PRIORITY_RE and nlp.HIGH_PRIORITY_RE.search(title)) or \
                          nlp.title_contains_disaster_keyword(title)
        
        # Confirmation of core signals
        has_hazard = diag["signals"].get("hazard_score", 0) > 0
        has_impact = diag["signals"].get("impact_hits", False)
        has_casualties = diag["signals"].get("impact_details", {}).get("deaths") or \
                         diag["signals"].get("impact_details", {}).get("missing")
        
        # Determine strictness based on title strength
        approval_threshold = CONF["threshold_approve_strong"] if is_strong_title else CONF["threshold_approve_strict"]
        
        # Fast-track Logic
        if has_casualties and has_hazard and score >= (approval_threshold - 1.0):
             # Bonus leniency for casualty reports with clear hazard context
             status = "approved"
        elif score >= approval_threshold:
            # [CRITICAL] Require hazard match (rule) or VIP term for auto-approve
            if has_hazard or diag["signals"].get("is_vip", False):
                status = "approved"
            else:
                status = "pending"
        elif score >= CONF["threshold_pass"]:
            status = "pending"
        elif (src.authority_level >= 2 or src.trusted) and score >= CONF["threshold_official"]:
            # [SAFETY NET] Official/Trusted sources are kept even with lower scores
            status = "pending"
            diag["reason"] = f"Pending (Official Source Fallback - Score {score:.1f})"

    if status == "auto-blacklisted":
        # Check database first
        try:
            exists = db.query(Blacklist).filter(Blacklist.news_hash == article_hash).first()
            if not exists:
                # Use a flush to trigger Integrity check early
                db.add(Blacklist(news_hash=article_hash, title=title, reason=f"Low Score: {score:.1f}"))
                db.flush()
        except Exception:
            db.rollback() # Ignore collision or race condition
        
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
        canonical_url=normalize_url(link),
        summary=meta["summary"],
        stage=meta["stage"],
        needs_verification=meta["needs_verification"],
        deaths=_get_impact_value(meta["impacts"]["deaths"]),
        missing=_get_impact_value(meta["impacts"]["missing"]),
        injured=_get_impact_value(meta["impacts"]["injured"]),
        damage_billion_vnd=_get_impact_value(meta["impacts"]["damage_billion_vnd"]),
        impact_details={**meta["impact_details"], "metrics": [meta["metrics"]]} if meta.get("metrics") else meta["impact_details"],
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

async def _process_article_logic(db, src, title, link, pub_at, summary):
    """
    Shared logic for ingesting, enriching, and saving an article.
    Used by both RSS and HTML scraper paths to ensure consistent validation.
    """
    article, status = await _ingest_article_async(db, src, title, link, pub_at, summary)
    
    if not article:
        return None, False, False, status

    await _enrich_article_async(db, src, article)
    
    # [FIX] Check for empty content (ghost article prevention)
    has_content = (article.summary and len(article.summary.strip()) > 10) or \
                  (article.full_text and len(article.full_text.strip()) > 50)
                  
    if not has_content:
        # logger.warning(f"   [SKIPPING] Empty content: {title[:50]}...")
        db.delete(article)
        return None, False, False, "empty_content"
    
    # Log status
    _log_artic_status(src.name, title, status, article.score)
    
    # Event Upsert
    ev, is_new = await asyncio.to_thread(upsert_event_for_article, db, article)
    return ev, is_new, True, status


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

        # 1. BATCH FETCH ALL FEEDS
        # This is the optimization: Fetch 50+ RSS feeds concurrently in one HTTPX session
        feed_results = await _fetch_all_feeds(all_feed_urls, headers={"User-Agent": settings.user_agent}, timeout_seconds=30, force_update=force_update)
        
        events_to_notify = [] # List of (event_id, is_new)
        
        # 2. PROCESS PER SOURCE
        for name, info in sources_info.items():
            src = info["source"]
            feeds = info["feeds"]
            
            stat = {"source": src.name, "articles_added": 0, "status": "pending", "error": None, "feed_used": [], "elapsed": 0}
            feed_worked = False
            
            # Prioritize: Primary -> Backup -> GNews
            for f_type, f_url in feeds:
                res = feed_results.get(f_url)
                if not res or res.get("error"):
                    continue
                
                if res.get("not_modified"):
                    # Nothing new
                    feed_worked = True
                    stat["feed_used"].append(f_type)
                    # Even if not modified, we consider it "working" (no error)
                    break
                    
                content = res.get("text", "")
                if not content: continue
                
                # Parse
                entry_list = []
                try:
                    parsed = feedparser.parse(content)
                    entry_list = parsed.entries
                except Exception: continue
                
                if not entry_list: continue
                
                feed_worked = True
                stat["feed_used"].append(f_type)
                
                # Process Entries Concurrently (Limited to 15 at once to avoid DB/Network overload)
                sem = asyncio.Semaphore(15)
                
                async def process_entry(entry):
                    # Each task gets its OWN DB session to avoid race conditions and session corruption
                    # especially when using asyncio.to_thread internally.
                    task_db = SessionLocal()
                    try:
                        async with sem:
                            title = html.unescape(html.unescape(getattr(entry, "title", ""))).strip()
                            title = re.sub(r"\s+", " ", title)
                            link = getattr(entry, "link", "").strip()
                            pub_at = _to_dt(entry)
                            if pub_at < CRAWL_MIN_DATE: return None
        
                            raw_sum = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                            sum_raw = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(html.unescape(raw_sum)))).strip()
                            
                            res = await _process_article_logic(task_db, src, title, link, pub_at, sum_raw)
                            if res and res[2]: # if article was added
                                ev_obj, is_new, added, status = res
                                ev_id = ev_obj.id if ev_obj else None
                                task_db.commit()
                                return ev_id, is_new, added, status
                            return res
                    finally:
                        task_db.close()

                tasks = [process_entry(e) for e in entry_list[:(50 if f_type == "gnews" else 200)]]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        ev_id, is_new, added, status = res
                        if added:
                            new_count += 1
                            info["added"] += 1
                            if ev_id: events_to_notify.append((ev_id, is_new))

                # If primary worked, we don't need backup/gnews
                if feed_worked: break
                
            # HTML Scraper Fallback
            force_html = any(x in src.domain for x in ["thoitietvietnam", "nchmf", "kttv"])
            if not feed_worked or force_html:
                try:
                    scraped = await HTMLScraper(timeout=settings.request_timeout_seconds).scrape_source(src.domain)
                    if scraped:
                        stat["feed_used"].append("html_scraper")
                        feed_worked = True
                        sem_scraped = asyncio.Semaphore(10)
                        async def process_scraped(item):
                            # Independent session for concurrent scraper results
                            task_db = SessionLocal()
                            try:
                                async with sem_scraped:
                                    res = await _process_article_logic(
                                        task_db, src, item["title"], item["url"], datetime.now(timezone.utc), item.get("summary", "")
                                    )
                                    if res and res[2]:
                                        ev_obj, is_new, added, status = res
                                        ev_id = ev_obj.id if ev_obj else None
                                        task_db.commit()
                                        return ev_id, is_new, added, status
                                    return res
                            finally:
                                task_db.close()
                        
                        scraped_tasks = [process_scraped(it) for it in scraped[:50]]
                        scraped_results = await asyncio.gather(*scraped_tasks)
                        
                        for res in scraped_results:
                            if res:
                                ev_id, is_new, added, status = res
                                if added:
                                    new_count += 1
                                    info["added"] += 1
                                    if ev_id: events_to_notify.append((ev_id, is_new))
                except Exception as e:
                    stat["error"] = f"scraper error: {str(e)[:50]}"
            
            if not feed_worked: stat["error"] = "all sources failed"
            stat["articles_added"] = info["added"]
            stat["feed_used"] = ", ".join(stat["feed_used"])
            per_source_stats.append(stat)
            
            # Batch Commit
            try:
                db.commit()
                # Notifications
                if events_to_notify:
                    unique_events = {}
                    for ev_id, is_new in events_to_notify:
                        if ev_id not in unique_events: unique_events[ev_id] = is_new
                        elif is_new: unique_events[ev_id] = True
                    
                    for ev_id, is_new in unique_events.items():
                        try:
                            # Safely emit notifications (threaded/async handled inside)
                            emit_event_notifications(db, ev_id, is_new=is_new)
                        except Exception: pass
                    events_to_notify = [] # clear for next source

            except Exception as e:
                db.rollback()
                stat["error"] = f"Commit failed: {e}"
            
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
            
            # Update Canonical URL if found in metadata
            if scraper_meta.get("canonical"):
                article.canonical_url = normalize_url(scraper_meta["canonical"])
            
            if real_date:
                # Sanity check: valid date and not in future
                if real_date < datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1):
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
            

            
            # [OPTIMIZATION]
            # Redundant upsert removed. The caller (craler loop) handles event upsert/updates.
            # await asyncio.to_thread(upsert_event_for_article, db, article)
            # db.flush()
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
        record = {"timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(), "new_articles": new_count, "elapsed": total_elapsed, "per_source": per_source}
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
    # Generate a lock key unique to this job configuration
    # This prevents multiple Gunicorn workers from running the exact same crawl job simultaneously
    lock_suffix = "full"
    if only_sources:
        import hashlib
        # Hash the sorted list of sources to create a deterministic key
        key_str = ",".join(sorted(only_sources))
        lock_suffix = hashlib.md5(key_str.encode()).hexdigest()
    
    lock_name = f"crawl_job_{lock_suffix}"
    
    # Try to acquire lock with 45 minutes TTL (crawls shouldn't take longer than this)
    if not cache.acquire_lock(lock_name, timeout=2700):
        # Lock acquisition failed = logic is running on another worker
        logger.info(f"[SCHEDULER] Skipping job {lock_name} - Locked by another worker.")
        return {"status": "skipped", "reason": "locked"}

    try:
        return asyncio.run(_process_once_async(force_update=force, only_sources=only_sources))
    finally:
        # Always release the lock so next run can proceed
        cache.release_lock(lock_name)

def cleanup_old_pending_articles():
    """Cleanup old pending articles and notifications to keep the DB lean."""
    db = SessionLocal()
    try:
        # 1. Old Pending Articles (> 30 days)
        limit_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        res = db.query(Article).filter(
            Article.status == "pending",
            Article.published_at < limit_date
        ).delete()
        
        # 2. Old Notifications (> 30 days)
        res_notif = db.query(models.Notification).filter(
            models.Notification.created_at < limit_date
        ).delete()
        
        db.commit()
        if res > 0 or res_notif > 0:
            logger.info(f"[CLEANUP] Removed {res} old pending articles and {res_notif} old notifications.")
    except Exception as e:
        logger.error(f"[CLEANUP] Failed: {e}")
    finally:
        db.close()

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
