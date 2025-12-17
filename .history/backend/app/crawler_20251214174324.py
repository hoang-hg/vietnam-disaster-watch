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
from pathlib import Path
from datetime import datetime, timezone
import feedparser
import httpx
import re
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
from .sources import SOURCES, build_gnews_rss
from . import nlp
from .dedup import find_duplicate_article, get_article_hash
from .event_matcher import upsert_event_for_article
from .html_scraper import HTMLScraper

Base.metadata.create_all(bind=engine)


def _to_dt(entry) -> datetime:
    tt = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if tt:
        return datetime(*tt[:6], tzinfo=timezone.utc).astimezone(timezone.utc).replace(tzinfo=None)
    return datetime.utcnow()


async def _fetch_all_feeds(feed_urls: list[str], headers: dict, timeout_seconds: int) -> dict:
    """Fetch all feeds concurrently. Returns mapping url -> dict(text/elapsed/error)."""
    results: dict = {}
    timeout = httpx.Timeout(timeout_seconds)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True, limits=limits) as client:
        tasks = {}
        for url in feed_urls:
            async def _get(u=url):
                start = time.perf_counter()
                try:
                    r = await client.get(u)
                    r.raise_for_status()
                    elapsed = time.perf_counter() - start
                    return (u, {"text": r.text, "elapsed": elapsed})
                except Exception as e:
                    elapsed = time.perf_counter() - start
                    return (u, {"error": str(e), "elapsed": elapsed})
            tasks[url] = asyncio.create_task(_get())

        for u, t in tasks.items():
            u_ret, data = await t
            results[u_ret] = data
    return results


async def _process_once_async() -> dict:
    """Async implementation of a single crawl run."""
    db: Session = SessionLocal()
    new_count = 0
    start_total = time.perf_counter()
    try:
        # Build list of feed urls with fallback chain per source
        sources_feeds: dict = {}  # source.name -> list of urls (primary, backup, gnews)
        for src in SOURCES:
            feed_urls = []
            
            # Add primary and backup RSS if available
            if src.primary_rss:
                feed_urls.append(("primary_rss", src.primary_rss))
            if src.backup_rss:
                feed_urls.append(("backup_rss", src.backup_rss))
            
            # Always add GNews fallback
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
            fetched = await _fetch_all_feeds(all_feed_urls, headers, settings.request_timeout_seconds)
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
                
                # Try to parse this feed
                elapsed = info.get("elapsed", 0)
                feed = feedparser.parse(info.get("text", ""))
                
                if not feed.entries:
                    print(f"[WARN] {src.name} {feed_type} returned 0 entries")
                    continue
                
                # Success! Use this feed
                stat["feed_used"] = feed_type
                stat["elapsed"] = elapsed
                src_info["used_feed"] = (feed_type, url)
                feed_worked = True
                
                print(f"[OK] {src.name} using {feed_type} ({len(feed.entries)} entries, {elapsed:.2f}s)")
                
                # Process articles from this feed
                max_articles = 30  # from sources.json config
                for entry in feed.entries[:max_articles]:
                    title = getattr(entry, "title", "").strip()
                    link = getattr(entry, "link", "").strip()
                    if not title or not link:
                        continue

                    published_at = _to_dt(entry)

                    text_for_nlp = title
                    disaster_type = nlp.classify_disaster(text_for_nlp)
                    province = nlp.extract_province(text_for_nlp)

                    impacts = nlp.extract_impacts(getattr(entry, "summary", "") or title)
                    summary = nlp.summarize((getattr(entry, "summary", "") or "").replace("&nbsp;", " "))

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
                        print(f"[DEDUP] {src.name} #{article_hash}: duplicate of {duplicate.source} (skipped)")
                        continue

                    article = Article(
                        source=src.name,
                        domain=src.domain,
                        title=title,
                        url=link,
                        published_at=published_at,
                        disaster_type=disaster_type,
                        province=province,
                        deaths=impacts["deaths"],
                        missing=impacts["missing"],
                        injured=impacts["injured"],
                        damage_billion_vnd=impacts["damage_billion_vnd"],
                        agency=impacts["agency"],
                        summary=summary,
                    )

                    try:
                        db.add(article)
                        db.flush()
                    except Exception:
                        db.rollback()
                        continue
                    
                    # Full-page fetch if impact keywords found
                    try:
                        should_fetch = False
                        text_lower = (title + "\n" + (getattr(entry, "summary", "") or "")).lower()
                        for klist in nlp.IMPACT_KEYWORDS.values():
                            for kw in klist:
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
                                    html = resp.text
                                    if _HAS_BS4 and BeautifulSoup is not None:
                                        soup = BeautifulSoup(html, "html.parser")
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
                                        article.deaths = full_impacts.get("deaths")
                                    if full_impacts.get("missing") is not None and article.missing is None:
                                        article.missing = full_impacts.get("missing")
                                    if full_impacts.get("injured") is not None and article.injured is None:
                                        article.injured = full_impacts.get("injured")
                                    if full_impacts.get("damage_billion_vnd") is not None and article.damage_billion_vnd is None:
                                        article.damage_billion_vnd = full_impacts.get("damage_billion_vnd")
                                    if full_impacts.get("agency") is not None and article.agency is None:
                                        article.agency = full_impacts.get("agency")
                                    if article.province in (None, "unknown"):
                                        prov = nlp.extract_province(full_text)
                                        if prov and prov != "unknown":
                                            article.province = prov
                                    try:
                                        article.full_text = full_text[:100000]
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass

                    upsert_event_for_article(db, article)
                    new_count += 1
                    src_info["articles_added"] += 1
                
                break  # Don't try other feeds for this source, we got articles
            
            if not feed_worked:
                # Try HTML scraper as final fallback if all feeds failed
                try:
                    print(f"[INFO] {src.name} - attempting HTML scraper fallback...")
                    scraper = HTMLScraper(timeout=settings.request_timeout_seconds)
                    scraped_articles = await scraper.scrape_source(src.domain)
                    
                    if scraped_articles:
                        stat["feed_used"] = "html_scraper"
                        stat["elapsed"] = 0
                        print(f"[OK] {src.name} using html_scraper ({len(scraped_articles)} articles)")
                        
                        # Process scraped articles
                        for scraped in scraped_articles[:30]:
                            title = scraped.get("title", "").strip()
                            url = scraped.get("url", "").strip()
                            if not title or not url:
                                continue
                            
                            # Use scrape time as publish time
                            published_at = datetime.utcnow()
                            
                            text_for_nlp = title
                            disaster_type = nlp.classify_disaster(text_for_nlp)
                            province = nlp.extract_province(text_for_nlp)
                            
                            impacts = nlp.extract_impacts(scraped.get("summary", "") or title)
                            summary = nlp.summarize(scraped.get("summary", ""))
                            
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
                                agency=impacts["agency"],
                                summary=summary,
                            )
                            
                            try:
                                db.add(article)
                                db.flush()
                                new_count += 1
                                src_info["articles_added"] += 1
                            except Exception:
                                db.rollback()
                                continue
                            
                            # Try to fetch full page for better impact extraction
                            try:
                                async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as aclient:
                                    resp = await aclient.get(url)
                                    resp.raise_for_status()
                                    html = resp.text
                                    
                                    if _HAS_BS4 and BeautifulSoup is not None:
                                        soup = BeautifulSoup(html, "html.parser")
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
                                        article.deaths = full_impacts.get("deaths")
                                    if full_impacts.get("missing") is not None and article.missing is None:
                                        article.missing = full_impacts.get("missing")
                                    if full_impacts.get("injured") is not None and article.injured is None:
                                        article.injured = full_impacts.get("injured")
                                    if full_impacts.get("damage_billion_vnd") is not None and article.damage_billion_vnd is None:
                                        article.damage_billion_vnd = full_impacts.get("damage_billion_vnd")
                                    if full_impacts.get("agency") is not None and article.agency is None:
                                        article.agency = full_impacts.get("agency")
                                    if article.province in (None, "unknown"):
                                        prov = nlp.extract_province(full_text)
                                        if prov and prov != "unknown":
                                            article.province = prov
                                    
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
                "timestamp": datetime.utcnow().isoformat(),
                "new_articles": new_count,
                "elapsed": total_elapsed,
                "per_source": per_source_stats,
            }
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARN] failed writing crawl log: {e}")

        return {"new_articles": new_count, "timestamp": datetime.utcnow().isoformat(), "elapsed": total_elapsed, "per_source": per_source_stats}
    finally:
        db.close()


def process_once() -> dict:
    """Synchronous wrapper used by the scheduler/background jobs.

    When called from a thread without a running event loop we can safely
    use asyncio.run to execute the async implementation. When the server
    startup wants to run the crawl immediately within the running event
    loop it should call `_process_once_async` directly and await it.
    """
    return asyncio.run(_process_once_async())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        print(process_once())
    else:
        print("Use --once; scheduling is handled by backend server.")


if __name__ == "__main__":
    main()
