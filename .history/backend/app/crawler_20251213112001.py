from __future__ import annotations
import argparse
import asyncio
import time
import json
from pathlib import Path
from datetime import datetime, timezone
import feedparser
import httpx
import re
from sqlalchemy.orm import Session
from .settings import settings
from .database import SessionLocal, engine, Base
from .models import Article
from .sources import SOURCES, build_gnews_rss
from . import nlp
from .event_matcher import upsert_event_for_article

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
        # Build list of feed urls
        to_fetch = []
        src_map = {}
        for src in SOURCES:
            feed_url = src.url if src.method == "rss" and src.url else build_gnews_rss(src.domain)
            to_fetch.append(feed_url)
            src_map[feed_url] = src

        headers = {"User-Agent": settings.user_agent}

        # Fetch concurrently with asyncio
        fetched = {}
        try:
            fetched = await _fetch_all_feeds(to_fetch, headers, settings.request_timeout_seconds)
        except Exception as e:
            print(f"[WARN] concurrent fetch failed: {e}")
            fetched = {}

        # Process feeds (gracefully handle errors) and collect per-source stats
        per_source_stats = []
        new_count_per_source: dict[str, int] = {src.name: 0 for src in SOURCES}

        for feed_url in to_fetch:
            src = src_map.get(feed_url)
            info = fetched.get(feed_url)
            stat = {"source": src.name, "url": feed_url, "elapsed": None, "error": None, "articles_added": 0}
            if info is None:
                stat["error"] = "no response"
                print(f"[WARN] no response for {src.name} ({feed_url})")
                per_source_stats.append(stat)
                continue
            if "error" in info:
                stat["error"] = info.get("error")
                stat["elapsed"] = info.get("elapsed", 0)
                print(f"[WARN] fetch {src.name} failed after {stat.get('elapsed', 0):.2f}s: {stat.get('error')}")
                per_source_stats.append(stat)
                continue

            stat["elapsed"] = info.get("elapsed", 0)
            feed = feedparser.parse(info["text"]) if info.get("text") is not None else None

            for entry in (feed.entries[:30] if feed is not None else []):
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
                # Conditional full-page fetch: only fetch article page if title/summary
                # contains impact-related keywords to avoid fetching every article.
                try:
                    should_fetch = False
                    text_lower = (title + "\n" + (getattr(entry, "summary", "") or "")).lower()
                    # check any impact keyword substrings
                    for klist in nlp.IMPACT_KEYWORDS.values():
                        for kw in klist:
                            if kw.lower() in text_lower:
                                should_fetch = True
                                break
                        if should_fetch:
                            break

                    if should_fetch:
                        # fetch full article page and run extraction on larger text
                        try:
                            timeout = settings.request_timeout_seconds
                            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as aclient:
                                resp = await aclient.get(link)
                                resp.raise_for_status()
                                html = resp.text
                                # extract <p> paragraphs as a simple heuristic
                                paras = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.I | re.S)
                                cleaned = []
                                for p in paras:
                                    t = re.sub(r"<[^>]+>", "", p)
                                    t = re.sub(r"\s+", " ", t).strip()
                                    if t:
                                        cleaned.append(t)
                                full_text = "\n\n".join(cleaned[:10]) if cleaned else re.sub(r"<[^>]+>", " ", html)
                                full_impacts = nlp.extract_impacts(full_text)
                                # update article fields if full-text found values
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
                                # try to update province from full text if unknown
                                if article.province in (None, "unknown"):
                                    prov = nlp.extract_province(full_text)
                                    if prov and prov != "unknown":
                                        article.province = prov
                        except Exception:
                            # ignore fetch failures and continue
                            pass
                except Exception:
                    # ensure crawling continues on unexpected errors
                    pass

                upsert_event_for_article(db, article)
                new_count += 1
                new_count_per_source[src.name] = new_count_per_source.get(src.name, 0) + 1

            stat["articles_added"] = new_count_per_source.get(src.name, 0)
            per_source_stats.append(stat)

        db.commit()
        total_elapsed = time.perf_counter() - start_total
        print(f"[INFO] crawl finished - new_articles={new_count} - elapsed={total_elapsed:.2f}s")

        # Ensure logs directory exists and append a JSON line with stats
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
