#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Research and test common RSS patterns for Vietnamese news sources.
Helps identify alternative RSS endpoints.
"""

import asyncio
import httpx
import feedparser
from pathlib import Path


# Common RSS URL patterns for Vietnamese news sites
RSS_PATTERNS = {
    "tuoitre.vn": [
        "https://tuoitre.vn/rss/thoi-su.rss",
        "https://tuoitre.vn/feed/rss.html",
        "https://tuoitre.vn/feed/",
        "https://tuoitre.vn/thoi-su/feed/",
        "https://tuoitre.vn/tin-tuc/feed/",
    ],
    "vnexpress.net": [
        "https://e.vnexpress.net/rss/thoi-su.rss",
        "https://vnexpress.net/rss/thoi-su.rss",
        "https://vnexpress.net/feed/thoi-su.rss",
        "https://vnexpress.net/feed/rss.html",
        "https://vnexpress.net/news/feed/",
    ],
    "dantri.com.vn": [
        "https://dantri.com.vn/thoi-su.rss",
        "https://dantri.com.vn/feed/thoi-su.rss",
        "https://dantri.com.vn/feed/rss.html",
        "https://dantri.com.vn/rss/",
    ],
    "baotintuc.vn": [
        "https://baotintuc.vn/rss/thoi-su.rss",
        "https://baotintuc.vn/feed/rss.html",
        "https://baotintuc.vn/feed/thoi-su/",
        "https://baotintuc.vn/tin-tuc/feed/",
    ],
    "sggp.org.vn": [
        "https://sggp.org.vn/rss/thoi-su.rss",
        "https://www.sggp.org.vn/rss/thoi-su.rss",
        "https://sggp.org.vn/feed/",
        "https://sggp.org.vn/feed/rss.html",
    ],
    "nld.com.vn": [
        "https://nld.com.vn/feed/rss.html",
        "https://nld.com.vn/feed/thoi-su.rss",
        "https://nld.com.vn/thoi-su.rss",
        "https://nld.com.vn/rss/thoi-su/",
    ],
    "vnanet.vn": [
        "https://vnanet.vn/rss/thoi-su.rss",
        "https://vnanet.vn/feed/rss.html",
        "https://vnanet.vn/feed/thoi-su/",
    ],
    "qdnd.vn": [
        "https://qdnd.vn/rss/thoi-su.rss",
        "https://qdnd.vn/feed/rss.html",
        "https://qdnd.vn/feed/thoi-su/",
    ],
    "baomoi.com": [
        # Baomoi is an aggregator, probably no RSS
        "https://baomoi.com/feed/rss.xml",
        "https://baomoi.com/feed/",
    ],
}


async def test_rss_url(url: str, timeout: int = 5) -> dict:
    """Test if an RSS URL is valid and returns entries."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            
            feed = feedparser.parse(resp.text)
            entries = len(feed.entries)
            
            return {
                "url": url,
                "status": 200,
                "entries": entries,
                "valid": entries > 0,
                "title": feed.feed.get("title", ""),
            }
    except httpx.HTTPStatusError as e:
        return {
            "url": url,
            "status": e.response.status_code,
            "entries": 0,
            "valid": False,
            "error": f"HTTP {e.response.status_code}",
        }
    except Exception as e:
        return {
            "url": url,
            "status": 0,
            "entries": 0,
            "valid": False,
            "error": str(e)[:50],
        }


async def search_rss_endpoints():
    """Test all RSS patterns for all sources."""
    print("\n🔍 Searching RSS endpoints...\n")
    
    results = {}
    
    for domain, patterns in RSS_PATTERNS.items():
        print(f"📰 {domain}")
        results[domain] = []
        
        # Test all patterns concurrently
        tasks = [test_rss_url(url) for url in patterns]
        test_results = await asyncio.gather(*tasks)
        
        for result in test_results:
            results[domain].append(result)
            
            if result["valid"]:
                print(f"  ✅ {result['url']}")
                print(f"     └─ {result['entries']} entries")
            else:
                status = result.get("status", "?")
                error = result.get("error", "unknown")
                print(f"  ❌ {result['url']}")
                print(f"     └─ {status}: {error}")
        
        print()
    
    # Generate summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY - Best RSS URLs Found")
    print("=" * 80 + "\n")
    
    best_urls = {}
    for domain, tests in results.items():
        valid = [t for t in tests if t["valid"]]
        if valid:
            # Pick the one with most entries
            best = max(valid, key=lambda x: x["entries"])
            best_urls[domain] = best["url"]
            print(f"✅ {domain:<30} → {best['url']}")
            print(f"   {best['entries']} entries")
        else:
            print(f"❌ {domain:<30} → NO WORKING RSS FOUND")
    
    print("\n" + "=" * 80)
    print(f"Found {len(best_urls)}/{len(RSS_PATTERNS)} working RSS sources")
    print("=" * 80 + "\n")
    
    return best_urls


if __name__ == "__main__":
    best = asyncio.run(search_rss_endpoints())
    
    # Print as JSON for sources.json update
    print("\n📋 Copy these to sources.json:\n")
    for domain, url in sorted(best.items()):
        print(f'      "primary_rss": "{url}",')
