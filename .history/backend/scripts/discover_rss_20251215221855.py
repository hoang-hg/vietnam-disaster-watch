"""
Discover RSS feeds for sources in backend/sources.json by probing common paths.
Updates primary_rss in place when a likely feed is found (backup saved).

Usage: python backend/scripts/discover_rss.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from time import sleep

try:
    import httpx
except Exception:
    httpx = None

try:
    import feedparser
except Exception:
    feedparser = None

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "sources.json"
BACKUP_FILE = ROOT / "sources.json.bak"

COMMON_PATHS = [
    "/rss",
    "/rss.xml",
    "/feed",
    "/feed.xml",
    "/atom.xml",
    "/rss/",
    "/feeds",
    "/feeds/rss.xml",
    "/index.xml",
]

HEADERS = {"User-Agent": "VietDisasterWatchBot/1.0 (+https://example.com)"}
TIMEOUT = 10


def is_feed_text(text: str) -> bool:
    low = text.lower()
    return "<rss" in low or "<feed" in low or "xml" in low and "rss" in low


def try_fetch(url: str) -> tuple[bool, str]:
    """Return (ok, text_or_error)"""
    try:
        if httpx is not None:
            r = httpx.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return True, r.text
        else:
            # fallback to urllib
            from urllib.request import Request, urlopen
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
                try:
                    return True, data.decode("utf-8", errors="ignore")
                except Exception:
                    return True, str(data)
    except Exception as e:
        return False, str(e)


def looks_like_feed(text: str) -> bool:
    if not text:
        return False
    if is_feed_text(text):
        return True
    if feedparser is not None:
        parsed = feedparser.parse(text)
        return bool(getattr(parsed, "entries", None))
    return False


def discover_for_domain(domain: str) -> str | None:
    schemes = ["https://", "http://"]
    for scheme in schemes:
        for p in COMMON_PATHS:
            url = scheme + domain.rstrip("/") + p
            ok, resp = try_fetch(url)
            if not ok:
                # skip errors quickly
                # print(f"{url} -> err: {resp}")
                continue
            if looks_like_feed(resp):
                return url
            sleep(0.1)
    # try homepage and look for common link rel
    for scheme in schemes:
        url = scheme + domain
        ok, resp = try_fetch(url)
        if not ok:
            continue
        low = resp.lower()
        # look for <link rel="alternate" type="application/rss+xml" href="...">
        import re
        m = re.search(r'<link[^>]+type=["\']application/(rss\+xml|atom\+xml)["\'][^>]*href=["\']([^"\']+)["\']', resp, flags=re.I)
        if m:
            href = m.group(2)
            # make absolute if needed
            from urllib.parse import urljoin
            feedurl = urljoin(url, href)
            ok2, resp2 = try_fetch(feedurl)
            if ok2 and looks_like_feed(resp2):
                return feedurl
    return None


def main():
    if not SOURCES_FILE.exists():
        print(f"sources.json not found at {SOURCES_FILE}")
        sys.exit(1)

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    sources = data.get("sources", [])
    updated = False

    for src in sources:
        domain = src.get("domain")
        if not domain:
            continue
        if src.get("primary_rss"):
            print(f"{domain} already has primary_rss: {src.get('primary_rss')}")
            continue
        print(f"Probing {domain} ...")
        found = discover_for_domain(domain)
        if found:
            print(f"  -> found feed: {found}")
            src["primary_rss"] = found
            updated = True
        else:
            print(f"  -> no feed found for {domain}")

    if updated:
        # backup then write
        try:
            if not BACKUP_FILE.exists():
                with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
                    json.dump(data, bf, ensure_ascii=False, indent=2)
        except Exception:
            pass
        with open(SOURCES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Updated {SOURCES_FILE} with discovered feeds.")
    else:
        print("No changes made.")


if __name__ == "__main__":
    main()
