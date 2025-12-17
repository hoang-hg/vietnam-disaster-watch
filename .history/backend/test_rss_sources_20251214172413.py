#!/usr/bin/env python3
"""Test RSS sources health and availability."""

import asyncio
import json
import time
from pathlib import Path
import httpx
import feedparser


async def test_rss_sources():
    """Test all RSS sources from sources.json."""
    sources_file = Path(__file__).parent / "sources.json"
    
    if not sources_file.exists():
        print(f"❌ sources.json not found at {sources_file}")
        return
    
    with open(sources_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    results = []
    timeout = httpx.Timeout(config.get("request_timeout", 10))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("Testing RSS sources...\n")
    
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        for src_data in config.get("sources", []):
            src_name = src_data["name"]
            primary_rss = src_data.get("primary_rss")
            backup_rss = src_data.get("backup_rss")
            
            print(f"📰 {src_name}")
            src_result = {
                "name": src_name,
                "domain": src_data["domain"],
                "primary": None,
                "backup": None,
                "note": src_data.get("note")
            }
            
            # Test primary RSS
            if primary_rss:
                try:
                    start = time.perf_counter()
                    resp = await client.get(primary_rss)
                    resp.raise_for_status()
                    elapsed = time.perf_counter() - start
                    
                    feed = feedparser.parse(resp.text)
                    entry_count = len(feed.entries)
                    
                    status = "✅" if entry_count > 0 else "⚠️"
                    print(f"  {status} Primary RSS: {entry_count} entries ({elapsed:.2f}s)")
                    src_result["primary"] = {
                        "status": "ok" if entry_count > 0 else "empty",
                        "entries": entry_count,
                        "elapsed": elapsed
                    }
                except Exception as e:
                    print(f"  ❌ Primary RSS: {str(e)[:60]}")
                    src_result["primary"] = {
                        "status": "error",
                        "error": str(e)[:60]
                    }
            else:
                print(f"  ⏭️  Primary RSS: not configured")
            
            # Test backup RSS
            if backup_rss:
                try:
                    start = time.perf_counter()
                    resp = await client.get(backup_rss)
                    resp.raise_for_status()
                    elapsed = time.perf_counter() - start
                    
                    feed = feedparser.parse(resp.text)
                    entry_count = len(feed.entries)
                    
                    status = "✅" if entry_count > 0 else "⚠️"
                    print(f"  {status} Backup RSS: {entry_count} entries ({elapsed:.2f}s)")
                    src_result["backup"] = {
                        "status": "ok" if entry_count > 0 else "empty",
                        "entries": entry_count,
                        "elapsed": elapsed
                    }
                except Exception as e:
                    print(f"  ❌ Backup RSS: {str(e)[:60]}")
                    src_result["backup"] = {
                        "status": "error",
                        "error": str(e)[:60]
                    }
            else:
                print(f"  ⏭️  Backup RSS: not configured")
            
            print()
            results.append(src_result)
    
    # Summary
    print("\n📊 SUMMARY")
    print("=" * 60)
    
    working = 0
    partial = 0
    failing = 0
    
    for res in results:
        primary_ok = res["primary"] and res["primary"].get("status") == "ok"
        backup_ok = res["backup"] and res["backup"].get("status") == "ok"
        
        if primary_ok or backup_ok:
            working += 1
            status_icon = "✅"
        elif res["primary"] and res["primary"].get("status") == "empty" or res["backup"] and res["backup"].get("status") == "empty":
            partial += 1
            status_icon = "⚠️"
        else:
            failing += 1
            status_icon = "❌"
        
        feed_used = "Primary" if primary_ok else ("Backup" if backup_ok else "None")
        print(f"{status_icon} {res['name']:<40} → {feed_used}")
    
    print("=" * 60)
    print(f"\n✅ Working: {working}/{len(results)}")
    print(f"⚠️  Partial: {partial}/{len(results)}")
    print(f"❌ Failing: {failing}/{len(results)}")
    print(f"\n💡 Recommendation:")
    if working >= len(results) * 0.8:
        print(f"   ✅ Most sources are working. Crawler should perform well.")
    elif working >= len(results) * 0.5:
        print(f"   ⚠️  Half of sources working. Consider investigating broken ones.")
    else:
        print(f"   ❌ Most sources failing. Check RSS URLs or network connectivity.")


if __name__ == "__main__":
    asyncio.run(test_rss_sources())
