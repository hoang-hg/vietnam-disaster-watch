import asyncio
import json
import feedparser
import httpx
from pathlib import Path
import sys
import time
from urllib.parse import urlparse
import urllib3

# Suppress SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
SOURCES_PATH = Path(__file__).resolve().parents[1] / "sources.json"
TIMEOUT = 15.0
USER_AGENT = "Mozilla/5.0 (compatible; VietDisasterBot/2.0; +http://github.com/example/bot)"

async def check_url(client, url):
    if not url:
        return None
    
    start = time.perf_counter()
    try:
        response = await client.get(url)
        elapsed = time.perf_counter() - start
        
        if response.status_code != 200:
            return {
                "status": "error",
                "code": response.status_code,
                "msg": f"HTTP {response.status_code}",
                "elapsed": elapsed
            }
        
        # Parse XML
        feed = feedparser.parse(response.text)
        
        if feed.bozo:
            pass
            
        entry_count = len(feed.entries)
        
        if entry_count == 0:
            return {
                "status": "empty",
                "code": 200,
                "msg": "0 entries (Empty)",
                "elapsed": elapsed,
                "entries": 0
            }
        
        # Check freshness
        latest = "Unknown"
        if entry_count > 0:
            e1 = feed.entries[0]
            if hasattr(e1, 'published'):
                latest = e1.published
            elif hasattr(e1, 'updated'):
                latest = e1.updated
                
        return {
            "status": "ok",
            "code": 200,
            "msg": f"OK ({entry_count} entries)",
            "elapsed": elapsed,
            "entries": entry_count,
            "latest": latest
        }

    except httpx.RequestError as e:
        return {
            "status": "error",
            "code": 0,
            "msg": f"Conn Error: {str(e)}",
            "elapsed": time.perf_counter() - start
        }
    except Exception as e:
        return {
            "status": "error",
            "code": 0,
            "msg": f"Error: {str(e)}",
            "elapsed": time.perf_counter() - start
        }

async def validate_all():
    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    log(f"Loading sources from: {SOURCES_PATH}")
    
    if not SOURCES_PATH.exists():
        log("❌ Error: sources.json not found!")
        return

    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    sources = data.get("sources", [])
    log(f"Found {len(sources)} sources defined.\n")
    
    headers = {"User-Agent": USER_AGENT}
    transport = httpx.AsyncHTTPTransport(retries=1, verify=False)
    
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, transport=transport, follow_redirects=True) as client:
        
        tasks = []
        for src in sources:
            name = src.get("name")
            p_rss = src.get("primary_rss")
            b_rss = src.get("backup_rss")
            
            if p_rss:
                tasks.append((name, "Primary", p_rss))
            if b_rss:
                tasks.append((name, "Backup", b_rss))
        
        log(f"{'SOURCE NAME':<25} | {'TYPE':<7} | {'STATUS':<25} | {'TIME':<6}")
        log("-" * 75)

        coroutines = [check_url(client, url) for _, _, url in tasks]
        outcomes = await asyncio.gather(*coroutines)
        
        stats = {"ok": 0, "error": 0, "empty": 0}
        
        for i, (name, rtype, url) in enumerate(tasks):
            res = outcomes[i]
            status_icon = "[UNK] "
            
            if res["status"] == "ok":
                status_icon = "[OK]  "
                stats["ok"] += 1
            elif res["status"] == "empty":
                status_icon = "[EMPTY]"
                stats["empty"] += 1
            else:
                status_icon = "[FAIL] "
                stats["error"] += 1
                
            elapsed_str = f"{res['elapsed']:.2f}s"
            msg = res['msg']
            if len(msg) > 25: msg = msg[:22] + "..."
            
            log(f"{status_icon} {name:<22} | {rtype:<7} | {msg:<25} | {elapsed_str}")
            
        log("-" * 75)
        log(f"SUMMARY: [OK] Healthy: {stats['ok']} | [EMPTY] Empty: {stats['empty']} | [FAIL] Broken: {stats['error']}")
        
        if stats['error'] > 0:
            log("\n[!] DETECTED BROKEN FEEDS: Consider setting them to null in sources.json")
        if stats['empty'] > 0:
            log("\n[!] DETECTED EMPTY FEEDS: Monitor or check URL.")

    # Save to file with UTF-8
    try:
        with open("validation_report.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("\nReport successfully saved to validation_report.txt")
    except Exception as e:
        print(f"\nFailed to save report: {e}")

if __name__ == "__main__":
    asyncio.run(validate_all())
