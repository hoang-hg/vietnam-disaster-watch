
import asyncio
import feedparser
import httpx
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import html
from pathlib import Path

# Setup path to import backend modules
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

try:
    from app import nlp
    from app import sources as src_module
except ImportError:
    import app.nlp as nlp
    import app.sources as src_module

import urllib3
urllib3.disable_warnings()

KTTV_KEYWORDS = ["KTTV", "nchmf", "khí tượng", "thủy văn"]

async def check_kttv():
    sources_file = backend_path / "sources.json"
    print(f"Loading sources configuration from {sources_file}...")
    all_sources = src_module.load_sources_from_json(str(sources_file))
    print(f"Loaded total {len(all_sources)} sources.")
    # Debug print names
    # for s in all_sources[:5]: print(f" - {s.name}")
    
    # Filter only KTTV sources
    # Case insensitive search
    kttv_sources = []
    for s in all_sources:
        if any(k.lower() in s.name.lower() for k in KTTV_KEYWORDS):
            kttv_sources.append(s)
            
    print(f"Found {len(kttv_sources)} KTTV sources to check.")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with httpx.AsyncClient(timeout=15.0, headers=headers, verify=False, follow_redirects=True) as client:
        for src in kttv_sources:
            print(f"\n--- Checking: {src.name} ({src.domain}) ---")
            
            # Determine URL (RSS or GNews fallback logic re-impl for test)
            url = src.primary_rss or src.backup_rss
            method = "RSS"
            if not url:
                url = src_module.build_gnews_rss(src.domain)
                method = "GNews"
                
            print(f"   URL ({method}): {url}")
            
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    print(f"   [ERROR] HTTP {resp.status_code}")
                    continue
                
                feed = feedparser.parse(resp.text)
                print(f"   fetched {len(feed.entries)} entries.")
                
                if not feed.entries:
                    print(f"   [WARNING] No entries found. Response sample: {resp.text[:200]}...")
                    continue

                for i, entry in enumerate(feed.entries[:5]): # Check first 5 items
                    title = html.unescape(entry.get("title", ""))
                    desc = html.unescape(entry.get("summary", "") or entry.get("description", ""))
                    
                    # NLP CHECK
                    is_valid = nlp.contains_disaster_keywords(desc, title=title, trusted_source=src.trusted)
                    status = "✅ ACCEPT" if is_valid else "❌ REJECT"
                    
                    print(f"   {i+1}. [{status}] {title[:60]}...")
                    if not is_valid:
                        # Diagonose why
                        sig = nlp.compute_disaster_signals(f"{title} {desc}")
                        print(f"      -> Reason match: {sig['rule_matches']}")
                        print(f"      -> Veto: {sig['absolute_veto']}")
                        
            except Exception as e:
                print(f"   [EXCEPTION] {e}")

if __name__ == "__main__":
    asyncio.run(check_kttv())
