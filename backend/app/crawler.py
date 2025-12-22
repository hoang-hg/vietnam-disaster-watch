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
from datetime import datetime, timezone
import random
import feedparser
import httpx
import re
import urllib3
# Suppress InsecureRequestWarning for cleaner logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# GLOBAL SSL PATCh: Allow Legacy Renegotiation
# Many VN sites (doisongphapluat, gov.vn) use older SSL config that OpenSSL 3 rejects.
# This forces Python to use a relaxed SSL context for urllib (used by feedparser).
import ssl
try:
    _ctx = ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE
    # OP_LEGACY_SERVER_CONNECT = 0x4 (Allows connecting to legacy servers)
    if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
         _ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    else:
         # Fallback for some python versions where attribute might be missing but bit works
         _ctx.options |= 0x4
    
    # 2. Allow Unsafe Legacy Renegotiation (Fix for baotintuc.vn)
    # This is often needed for older OpenSSL 3+ systems connecting to ancient servers
    try:
        # constant might not be exposed in all python versions, value is 0x40000 
        _ctx.options |= getattr(ssl, "OP_legacy_server_connect", 0x4)
        # Some OS/Distros need system configuration, but in python we can try to set the option manually:
        # Note: In strict OpenSSL 3 environments, this might still fail if global conf forbids it.
        # Check if we can lower security level (only works on some systems)
        if hasattr(_ctx, 'set_ciphers'):
            _ctx.set_ciphers('DEFAULT@SECLEVEL=1')
    except Exception:
        pass

    # Apply globally to urllib (which feedparser uses)
    ssl._create_default_https_context = lambda: _ctx
except Exception as e:
    print(f"[WARN] Failed to apply SSL patch: {e}")
try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    BeautifulSoup = None
    _HAS_BS4 = False
from sqlalchemy.orm import Session
from .settings import settings
from .database import SessionLocal, engine, Base
from .models import Article
from .sources import SOURCES, build_gnews_rss, CONFIG
from . import nlp
from .dedup import find_duplicate_article, get_article_hash
from .event_matcher import upsert_event_for_article
from .html_scraper import HTMLScraper, fetch_article_full_text

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

# Optional classifier loader (joblib). If model exists, use as second-pass.
_classifier = None
try:
    import joblib
    from pathlib import Path
    model_path = Path(__file__).resolve().parents[1] / 'models' / 'light_classifier.joblib'
    if model_path.exists():
        _classifier = joblib.load(model_path)
except Exception:
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
        return datetime(*tt[:6], tzinfo=timezone.utc).astimezone(timezone.utc).replace(tzinfo=None)
    return datetime.now(timezone.utc).replace(tzinfo=None)

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

    # 2. Check HTML soup (og:image)
    if soup:
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
        
        twitter_image = soup.find("meta", name="twitter:image")
        if twitter_image and twitter_image.get("content"):
            return twitter_image["content"]
        
        # fallback: find first large image inside article body? 
        # Risky without complex logic, stick to meta tags for now.
    
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
    timeout = httpx.Timeout(timeout_seconds)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    
    # Default headers for feed fetching
    default_headers = {
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
    }
    headers = {**default_headers, **headers}

    # load persisted feed state for ETag/Last-Modified
    feed_state = _load_feed_state()

    # Allow insecure SSL (verify=False) to support gov sites with bad certs
    transport = httpx.AsyncHTTPTransport(retries=3, verify=False)
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, limits=limits, transport=transport) as client:
        tasks = {}
        for url in feed_urls:
            async def _get(u=url):
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

                        r = await client.get(u, headers=local_headers)
                        
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
                                _save_feed_state(feed_state)
                        except Exception:
                            pass

                        return (u, {"text": r.text, "elapsed": elapsed, "status_code": r.status_code})
                        
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

    return results



async def _process_once_async(force_update: bool = False, only_sources: list[str] = None) -> dict:
    """Async implementation of a single crawl run."""
    db: Session = SessionLocal()
    new_count = 0
    start_total = time.perf_counter()
    try:
        # Build list of feed urls with fallback chain per source
        sources_feeds: dict = {}  # source.name -> list of urls (primary, backup, gnews)
        for src in SOURCES:
            if only_sources and src.name not in only_sources:
                continue
                
            feed_urls = []
            
            # Add primary and backup RSS if available
            if src.primary_rss:
                feed_urls.append(("primary_rss", src.primary_rss))
            if src.backup_rss:
                feed_urls.append(("backup_rss", src.backup_rss))
            
            # Always add GNews fallback with context terms from config
            gnews_context = CONFIG.get("gnews_context_terms", [])
            if gnews_context:
                # Use context terms for better filtering
                gnews_url = build_gnews_rss(src.domain, context_terms=gnews_context)
                print(f"[DEBUG] {src.name} GNews with {len(gnews_context)} context terms")
            else:
                # Fallback to no context terms
                gnews_url = build_gnews_rss(src.domain)
            feed_urls.append(("gnews", gnews_url))
            
            sources_feeds[src.name] = {
                "source": src,
                "feed_urls": feed_urls,
                "used_feed": None,
                "articles_added": 0
            }

        headers = {"User-Agent": settings.user_agent}

        # Fetch all feeds concurrently
        all_feed_urls = []
        feed_to_source_info: dict = {}  # (url, feed_type) -> source_info
        
        for src_name, src_info in sources_feeds.items():
            for feed_type, url in src_info["feed_urls"]:
                all_feed_urls.append(url)
                feed_to_source_info[url] = (src_name, feed_type)

        fetched = {}
        try:
            fetched = await _fetch_all_feeds(all_feed_urls, headers, settings.request_timeout_seconds, force_update=force_update)
        except Exception as e:
            print(f"[WARN] concurrent fetch failed: {e}")
            fetched = {}

        # Try fallback chain per source: primary → backup → gnews
        per_source_stats = []
        
        for src_name, src_info in sources_feeds.items():
            src = src_info["source"]
            stat = {"source": src.name, "feed_used": None, "elapsed": None, "error": None, "articles_added": 0}
            
            feed_worked = False
            for feed_type, url in src_info["feed_urls"]:
                info = fetched.get(url)

                if info is None or "error" in info:
                    elapsed = info.get("elapsed", 0) if info else 0
                    err = info.get("error", "no response") if info else "no response"
                    print(f"[WARN] {src.name} {feed_type} failed ({elapsed:.2f}s): {err}")
                    continue

                # If feed did not change since last fetch (HTTP 304), treat as a successful feed with no new entries
                if info.get("not_modified"):
                    elapsed = info.get("elapsed", 0)
                    stat["feed_used"] = f"{stat['feed_used']}, {feed_type}" if stat["feed_used"] else feed_type
                    stat["elapsed"] = (stat["elapsed"] or 0) + elapsed
                    feed_worked = True
                    print(f"[OK] {src.name} using {feed_type} (not modified, {elapsed:.2f}s)")
                    # DO NOT BREAK: Continue to check next feed (e.g. backup/secondary)
                    continue
                
                # Try to parse this feed
                elapsed = info.get("elapsed", 0)
                feed = feedparser.parse(info.get("text", ""))
                
                if not feed.entries:
                    print(f"[WARN] {src.name} {feed_type} returned 0 entries")
                    continue
                
                # Success! Use this feed
                stat["feed_used"] = f"{stat['feed_used']}, {feed_type}" if stat["feed_used"] else feed_type
                stat["elapsed"] = (stat["elapsed"] or 0) + elapsed
                feed_worked = True
                
                print(f"[OK] {src.name} using {feed_type} ({len(feed.entries)} entries, {elapsed:.2f}s)")
                
                # Process articles from this feed
                # DO NOT BREAK: Continue to process other feeds (e.g. backup/secondary) to maximize coverage
                max_articles = 200  # User requested deep crawl
                for entry in feed.entries[:max_articles]:
                    title = html.unescape(getattr(entry, "title", "")).strip()
                    link = getattr(entry, "link", "").strip()
                    
                    published_at = _to_dt(entry)
                    summary_raw = html.unescape(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
                    text_for_nlp = title + " " + summary_raw
                    # ---------------------------------------------------------
                    # 1. OPTIMIZATION: Advanced NLP Check (Title + Summary + Trust)
                    # ---------------------------------------------------------
                    # Uses Smart Filtering: 
                    # - Trusted sources passed easier.
                    # - Untrusted sources need Impact/Metrics.
                    # - Hard Negatives filtered out.
                    is_relevant = nlp.contains_disaster_keywords(summary_raw, title=title, trusted_source=src.trusted)
                    
                    if not is_relevant:
                        continue

                    # Second-pass: optional classifier rejects low-probability items
                    try:
                        if _classifier is not None:
                            text_for_classify = (title + "\n" + (getattr(entry, "summary", "") or "")).strip()
                            prob = None
                            try:
                                prob = float(_classifier.predict_proba([text_for_classify])[0][1])
                            except Exception:
                                # some sklearn models expose predict_proba differently
                                prob = None
                            if prob is not None:
                                # configurable threshold (0.5 by default)
                                if prob < 0.5:
                                    # log classifier skip
                                    try:
                                        logs_dir = Path(__file__).resolve().parents[1] / "logs"
                                        logs_dir.mkdir(parents=True, exist_ok=True)
                                        skip_file = logs_dir / "skip_debug.jsonl"
                                        record = {
                                            "timestamp": datetime.utcnow().isoformat(),
                                            "action": "skip_classifier",
                                            "source": src.name,
                                            "domain": src.domain,
                                            "title": title,
                                            "url": link,
                                            "id": get_article_hash(title, src.domain),
                                            "classifier_prob": prob,
                                        }
                                        with skip_file.open("a", encoding="utf-8") as f:
                                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                                    except Exception:
                                        pass
                                    print(f"[SKIP_CLASSIFIER] {src.name} #{record['id']}: prob={prob:.2f}")
                                    continue
                    except Exception:
                        pass
                    
                    disaster_info = nlp.classify_disaster(text_for_nlp)
                    disaster_type = disaster_info.get("primary_type", "unknown")
                    province = nlp.extract_province(text_for_nlp)

                    impacts = nlp.extract_impacts(summary_raw or title)
                    summary_text = nlp.summarize(summary_raw.replace("&nbsp;", " "))
                    
                    # Detect Event Stage (Warning vs Impact vs Recovery)
                    stage = nlp.determine_event_stage(text_for_nlp)
                    summary = f"[{stage}] {summary_text}"


                    # Check for duplicates before inserting
                    duplicate = find_duplicate_article(
                        db,
                        src.domain,
                        link,
                        title,
                        published_at,
                        time_window_hours=24
                    )
                    
                    if duplicate:
                        # Link to existing article instead of creating duplicate
                        article_hash = get_article_hash(title, src.domain)
                        logger.info(f"Skipping duplicate article: {title[:50]}... (hash={article_hash})")
                        continue

                    article = Article(
                        source=src.name,
                        domain=src.domain,
                        title=title,
                        url=link,
                        published_at=published_at,
                        disaster_type=disaster_type,
                        province=province,
                        deaths=_get_impact_value(impacts["deaths"]),
                        missing=_get_impact_value(impacts["missing"]),
                        injured=_get_impact_value(impacts["injured"]),
                        damage_billion_vnd=_get_impact_value(impacts["damage_billion_vnd"]),
                        agency=impacts["agency"][:255] if impacts["agency"] else None,
                        summary=summary,
                        image_url=_extract_image_url(entry),
                        impact_details=nlp.extract_impact_details(text_for_nlp) 
                    )

                    try:
                        db.add(article)
                        db.flush()
                        new_count += 1
                        src_info["articles_added"] += 1
                        print(f"   [ADDED] {src.name}: {title[:70]}...")
                    except Exception as e:
                        db.rollback()
                        print(f"   [ERROR_DB] {src.name}: {e}")
                        continue

                    # Log accepted/inserted candidate (for review)
                    try:
                        logs_dir = Path(__file__).resolve().parents[1] / "logs"
                        logs_dir.mkdir(parents=True, exist_ok=True)
                        skip_file = logs_dir / "skip_debug.jsonl"
                        article_hash = get_article_hash(title, src.domain, link)
                        record = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "action": "accepted",
                            "source": src.name,
                            "domain": src.domain,
                            "title": title,
                            "url": link,
                            "id": article_hash,
                            "disaster_type": disaster_type,
                            "province": province,
                            "diagnose": nlp.diagnose(text_for_nlp),
                        }
                        with skip_file.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    except Exception:
                        pass
                    
                    # Full-page fetch if impact keywords found
                    try:
                        # Fetch full HTML for trusted sources, for title-matched entries,
                        # or when impact keywords are present in feed summary.
                        should_fetch = False
                        text_lower = (title + "\n" + (getattr(entry, "summary", "") or "")).lower()
                        if src.trusted or nlp.title_contains_disaster_keyword(title):
                            should_fetch = True
                        else:
                            for data in nlp.IMPACT_KEYWORDS.values():
                                terms = data.get("terms", [])
                                for kw in terms:
                                    if kw.lower() in text_lower:
                                        should_fetch = True
                                        break
                                if should_fetch:
                                    break

                        if should_fetch:
                            try:
                                timeout = settings.request_timeout_seconds
                                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as aclient:
                                    resp = await aclient.get(link)
                                    resp.raise_for_status()
                                    page_html = resp.text
                                    if _HAS_BS4 and BeautifulSoup is not None:
                                        soup = BeautifulSoup(page_html, "html.parser")
                                        paras = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
                                        cleaned = [re.sub(r"\s+", " ", p).strip() for p in paras if p and p.strip()]
                                        full_text = "\n\n".join(cleaned[:10]) if cleaned else soup.get_text(separator=" ", strip=True)
                                    else:
                                        paras = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.I | re.S)
                                        cleaned = []
                                        for p in paras:
                                            t = re.sub(r"<[^>]+>", "", p)
                                            t = re.sub(r"\s+", " ", t).strip()
                                            if t:
                                                cleaned.append(t)
                                        full_text = "\n\n".join(cleaned[:10]) if cleaned else re.sub(r"<[^>]+>", " ", html)

                                    full_impacts = nlp.extract_impacts(full_text)
                                    if full_impacts.get("deaths") is not None and article.deaths is None:
                                        article.deaths = _get_impact_value(full_impacts.get("deaths"))
                                    if full_impacts.get("missing") is not None and article.missing is None:
                                        article.missing = _get_impact_value(full_impacts.get("missing"))
                                    if full_impacts.get("injured") is not None and article.injured is None:
                                        article.injured = _get_impact_value(full_impacts.get("injured"))
                                    if full_impacts.get("damage_billion_vnd") is not None and article.damage_billion_vnd is None:
                                        article.damage_billion_vnd = _get_impact_value(full_impacts.get("damage_billion_vnd"))
                                    if full_impacts.get("agency") is not None and article.agency is None:
                                        raw_agency = full_impacts.get("agency")
                                        article.agency = raw_agency[:255] if raw_agency else None
                                    if article.province in (None, "unknown"):
                                        prov = nlp.extract_province(full_text)
                                        if prov and prov != "unknown":
                                            article.province = prov
                                    
                                    # Attempt to extract image from soup if missing
                                    if not article.image_url and _HAS_BS4 and BeautifulSoup is not None and 'soup' in locals():
                                        img = _extract_image_url(None, soup=soup)
                                        if img:
                                            article.image_url = img

                                    try:
                                        article.full_text = full_text[:100000]
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass

                    upsert_event_for_article(db, article)
                
                break  # Don't try other feeds for this source, we got articles
            
                break  # Don't try other feeds for this source, we got articles
            
            # Force HTML scraper for known difficult sources w/ custom scrapers
            force_html_scrape = "thoitietvietnam" in src.domain or "nchmf" in src.domain or "kttv" in src.domain

            if (not feed_worked) or force_html_scrape:
                # Try HTML scraper
                try:
                    if force_html_scrape:
                         print(f"[INFO] {src.name} - forcing HTML scraper execution...")
                    else:
                         print(f"[INFO] {src.name} - attempting HTML scraper fallback...")

                    scraper = HTMLScraper(timeout=settings.request_timeout_seconds)
                    scraped_articles = await scraper.scrape_source(src.domain)
                    
                    if scraped_articles:
                        stat["feed_used"] = f"{stat['feed_used']}, html_scraper" if stat["feed_used"] else "html_scraper"
                        # Reset elapsed since this is async/parallel to feed
                        # stat["elapsed"] += ... 
                        print(f"[OK] {src.name} using html_scraper ({len(scraped_articles)} articles)")
                        
                        # Process scraped articles
                        for scraped in scraped_articles[:30]:
                            title = html.unescape(scraped.get("title", "")).strip()
                            url = scraped.get("url", "").strip()
                            if not title or not url:
                                continue
                            
                            # Use scrape time as publish time
                            published_at = datetime.utcnow()
                            
                            summary_raw_scraper = html.unescape(scraped.get("summary", "") or scraped.get("description", "") or "")
                            text_for_nlp = title + " " + summary_raw_scraper
                            
                            # Pre-filter using main NLP: 
                            # - Explicitly check using full NLP (Veto/Rules)
                            # - Pass trusted_source=src.trusted to allow lighter threshold for official sources
                            if not nlp.contains_disaster_keywords(summary_raw_scraper, title=title, trusted_source=src.trusted):
                                article_hash = get_article_hash(title, src.domain)
                                diag = nlp.diagnose(title)
                                print(f"[SKIP] {src.name} #{article_hash}: nlp-rejected score={diag['score']:.1f} reason={diag['reason']}")
                                continue
                            
                            
                            disaster_info = nlp.classify_disaster(text_for_nlp)
                            disaster_type = disaster_info.get("primary_type", "unknown")
                            province = nlp.extract_province(text_for_nlp)
                            
                            impacts = nlp.extract_impacts(summary_raw_scraper or title)
                            summary = nlp.summarize(summary_raw_scraper)
                            
                            # Check for duplicates
                            duplicate = find_duplicate_article(
                                db,
                                src.domain,
                                url,
                                title,
                                published_at,
                                time_window_hours=24
                            )
                            
                            if duplicate:
                                article_hash = get_article_hash(title, src.domain)
                                print(f"[DEDUP] {src.name} #{article_hash}: duplicate (skipped)")
                                continue
                            
                            article = Article(
                                source=src.name,
                                domain=src.domain,
                                title=title,
                                url=url,
                                published_at=published_at,
                                disaster_type=disaster_type,
                                province=province,
                                deaths=impacts["deaths"],
                                missing=impacts["missing"],
                                injured=impacts["injured"],
                                damage_billion_vnd=impacts["damage_billion_vnd"],
                                agency=impacts["agency"][:255] if impacts["agency"] else None,
                                summary=summary,
                                impact_details=nlp.extract_impact_details(text_for_nlp)
                            )
                            
                            try:
                                db.add(article)
                                db.flush()
                                new_count += 1
                                src_info["articles_added"] += 1
                                print(f"   [ADDED_SCRAPE] {src.name}: {title[:70]}...")
                                upsert_event_for_article(db, article)
                            except Exception as e:
                                db.rollback()
                                print(f"   [ERROR_DB_SCRAPE] {src.name}: {e}")
                                continue
                            
                            # Try to fetch full page for better impact extraction
                            try:
                                async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as aclient:
                                    resp = await aclient.get(url)
                                    resp.raise_for_status()
                                    resp.raise_for_status()
                                    page_html = resp.text
                                    
                                    if _HAS_BS4 and BeautifulSoup is not None:
                                        soup = BeautifulSoup(page_html, "html.parser")
                                        paras = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
                                        cleaned = [re.sub(r"\s+", " ", p).strip() for p in paras if p and p.strip()]
                                        full_text = "\n\n".join(cleaned[:10]) if cleaned else soup.get_text(separator=" ", strip=True)
                                    else:
                                        paras = re.findall(r"<p[^>]*>(.*?)</p>", page_html, flags=re.I | re.S)
                                        cleaned = []
                                        for p in paras:
                                            t = re.sub(r"<[^>]+>", "", p)
                                            t = re.sub(r"\s+", " ", t).strip()
                                            if t:
                                                cleaned.append(t)
                                        full_text = "\n\n".join(cleaned[:10]) if cleaned else re.sub(r"<[^>]+>", " ", page_html)
                                    
                                    full_impacts = nlp.extract_impacts(full_text)
                                    if full_impacts.get("deaths") is not None and article.deaths is None:
                                        article.deaths = _get_impact_value(full_impacts.get("deaths"))
                                    if full_impacts.get("missing") is not None and article.missing is None:
                                        article.missing = _get_impact_value(full_impacts.get("missing"))
                                    if full_impacts.get("injured") is not None and article.injured is None:
                                        article.injured = _get_impact_value(full_impacts.get("injured"))
                                    if full_impacts.get("damage_billion_vnd") is not None and article.damage_billion_vnd is None:
                                        article.damage_billion_vnd = _get_impact_value(full_impacts.get("damage_billion_vnd"))
                                    if full_impacts.get("agency") is not None and article.agency is None:
                                        raw_agency = full_impacts.get("agency")
                                        article.agency = raw_agency[:255] if raw_agency else None
                                    if article.province in (None, "unknown"):
                                        prov = nlp.extract_province(full_text)
                                        if prov and prov != "unknown":
                                            article.province = prov
                                    
                                    # Attempt to extract image from soup if missing
                                    if not article.image_url and _HAS_BS4 and BeautifulSoup is not None and 'soup' in locals():
                                        img = _extract_image_url(None, soup=soup)
                                        if img:
                                            article.image_url = img
                                    
                                    db.commit()
                            except Exception:
                                pass
                        
                        feed_worked = True
                    else:
                        stat["error"] = "all feeds and scraper failed"
                        print(f"[ERROR] {src.name} - html scraper returned no articles")
                except Exception as e:
                    stat["error"] = f"scraper error: {str(e)[:50]}"
                    print(f"[ERROR] {src.name} - html scraper failed: {e}")
                
                if not feed_worked:
                    stat["error"] = "all feeds and scraper failed"
                    print(f"[ERROR] {src.name} - all feed sources and scraper failed")
            
            stat["articles_added"] = src_info["articles_added"]
            per_source_stats.append(stat)

        db.commit()
        total_elapsed = time.perf_counter() - start_total
        print(f"[INFO] crawl finished - new_articles={new_count} - elapsed={total_elapsed:.2f}s")

        # Log crawl results
        try:
            logs_dir = Path(__file__).resolve().parents[1] / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / "crawl_log.jsonl"
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "new_articles": new_count,
                "elapsed": total_elapsed,
                "per_source": per_source_stats,
            }
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARN] failed writing crawl log: {e}")

        return {"new_articles": new_count, "timestamp": datetime.now(timezone.utc).isoformat(), "elapsed": total_elapsed, "per_source": per_source_stats}
    finally:
        db.close()

def process_once(force: bool = False, only_sources: list[str] = None) -> dict:
    """Synchronous wrapper used by the scheduler/background jobs."""
    return asyncio.run(_process_once_async(force_update=force, only_sources=only_sources))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--force", action="store_true", help="Ignore feed cache and force re-crawl")
    args = parser.parse_args()
    if args.once:
        print(process_once(force=args.force))
    else:
        print("Use --once; scheduling is handled by backend server.")


if __name__ == "__main__":
    main()
