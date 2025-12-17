from __future__ import annotations
import argparse
import asyncio
import time
from datetime import datetime, timezone
import feedparser
import httpx
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


def process_once() -> dict:
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
            fetched = asyncio.run(_fetch_all_feeds(to_fetch, headers, settings.request_timeout_seconds))
        except Exception as e:
            print(f"[WARN] concurrent fetch failed: {e}")
            fetched = {}

        # Process feeds (gracefully handle errors)
        for feed_url in to_fetch:
            src = src_map.get(feed_url)
            info = fetched.get(feed_url)
            if info is None:
                print(f"[WARN] no response for {src.name} ({feed_url})")
                continue
            if "error" in info:
                print(f"[WARN] fetch {src.name} failed after {info.get('elapsed', 0):.2f}s: {info.get('error')}")
                continue

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

                upsert_event_for_article(db, article)
                new_count += 1

        db.commit()
        total_elapsed = time.perf_counter() - start_total
        print(f"[INFO] crawl finished - new_articles={new_count} - elapsed={total_elapsed:.2f}s")
        return {"new_articles": new_count, "timestamp": datetime.utcnow().isoformat(), "elapsed": total_elapsed}
    finally:
        db.close()


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
