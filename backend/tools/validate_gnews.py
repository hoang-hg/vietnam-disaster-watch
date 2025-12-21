
import asyncio
import sys
import json
from pathlib import Path
import time
import feedparser
import httpx
import logging

# Add backend to path to allow imports from app
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

from app.sources import build_gnews_rss, load_sources_from_json, CONFIG

# Suppress excessive logging
logging.getLogger("httpx").setLevel(logging.WARNING)

async def check_gnews_feed(client, source):
    # Get context terms if any (global config)
    context_terms = CONFIG.get("gnews_context_terms", [])
    
    # Generate URL
    url = build_gnews_rss(source.domain, context_terms=context_terms)
    
    start = time.perf_counter()
    try:
        response = await client.get(url)
        elapsed = time.perf_counter() - start
        
        if response.status_code != 200:
            return {
                "name": source.name,
                "domain": source.domain,
                "status": "error",
                "code": response.status_code,
                "msg": f"HTTP {response.status_code}",
                "elapsed": elapsed,
                "count": 0,
                "url": url
            }
        
        feed = feedparser.parse(response.text)
        count = len(feed.entries)
        
        status = "ok" if count > 0 else "empty"
        
        return {
            "name": source.name,
            "domain": source.domain,
            "status": status,
            "code": 200,
            "msg": f"{count} entries",
            "elapsed": elapsed,
            "count": count,
            "url": url
        }

    except Exception as e:
        return {
            "name": source.name,
            "domain": source.domain,
            "status": "error",
            "code": 0,
            "msg": str(e)[:30],
            "elapsed": time.perf_counter() - start,
            "count": 0,
            "url": url
        }

async def validate_all_gnews():
    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    log(f"Loading sources...")
    sources = load_sources_from_json()
    log(f"Found {len(sources)} sources. Checking GNews fallback availability...\n")
    
    log(f"{'SOURCE':<25} | {'DOMAIN':<25} | {'STATUS':<8} | {'COUNT':<5} | {'TIME'}")
    log("-" * 85)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
        tasks = [check_gnews_feed(client, src) for src in sources]
        results = await asyncio.gather(*tasks)
        
        stats = {"ok": 0, "empty": 0, "error": 0}
        
        for r in results:
            if r["status"] == "ok":
                stats["ok"] += 1
                status_str = "✅ OK"
            elif r["status"] == "empty":
                stats["empty"] += 1
                status_str = "⚠️ EMPTY"
            else:
                stats["error"] += 1
                status_str = "❌ FAIL"
            
            log(f"{r['name']:<25} | {r['domain']:<25} | {status_str:<8} | {r['count']:<5} | {r['elapsed']:.2f}s")
            
        log("-" * 85)
        log(f"SUMMARY: Healthy: {stats['ok']} | Empty: {stats['empty']} | Failed: {stats['error']}")
        log(f"Note: 'Empty' usually means Google News has no recent indexed articles matching the disaster keywords for that domain.")

    with open("gnews_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nReport saved to gnews_report.txt")

if __name__ == "__main__":
    asyncio.run(validate_all_gnews())
