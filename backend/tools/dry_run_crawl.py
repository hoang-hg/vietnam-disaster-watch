import asyncio
import feedparser
import httpx
import sys
import html # For unescaping entities
from pathlib import Path

# Setup path to import backend modules
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

try:
    from app import nlp
    from app import sources as src_module
except ImportError:
    # Fallback if running from root
    import app.nlp as nlp
    import app.sources as src_module

import urllib3
urllib3.disable_warnings()

async def dry_run():
    print("Loading sources configuration...")
    sources = src_module.load_sources_from_json()
    print(f"Loaded {len(sources)} sources definition.")
    
    total_scanned = 0
    total_accepted = 0
    accepted_details = []
    rejected_samples = [] 
    
    print("\n🚀 STARTING CRAWL SIMULATION (Scanning all feeds)...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with httpx.AsyncClient(timeout=10.0, headers=headers, verify=False, follow_redirects=True) as client:
        tasks = []
        for src in sources:
            # 1. Determine Feed URL
            url = src.primary_rss or src.backup_rss
            method = "RSS"
            
            if not url and src.domain:
                # Fallback to GNews if no RSS
                try:
                    url = src_module.build_gnews_rss(src.domain)
                    method = "GNews"
                except:
                    continue
            
            if url:
                tasks.append(fetch_and_process(client, src.name, url, method))
        
        # Run all requests concurrently
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        for r in results:
            total_scanned += r["total"]
            total_accepted += r["accepted"]
            accepted_details.extend(r["accepted_items"])
            # Collect some rejected items for inspection (noise)
            if r["rejected_items"]:
                rejected_samples.append(r["rejected_items"][0]) 

    # --- REPORT ---
    rate = (total_accepted / total_scanned * 100) if total_scanned else 0
    
    print("\n" + "="*60)
    print(f"📊 CRAWL RESULT SUMMARY")
    print(f"Total Sources Checked:      {len(tasks)}")
    print(f"Total Articles Scanned:     {total_scanned}")
    print(f"Total Disaster News Found:  {total_accepted}")
    print(f"Relevance Rate:             {rate:.2f}%")
    
    # Save to Text File for User Verification
    import time
    with open("crawled_news_list.txt", "w", encoding="utf-8") as f:
        f.write(f"DANH SACH TIN THIEN TAI LOC DUOC ({time.strftime('%H:%M %d/%m/%Y')})\n")
        f.write(f"Tong so tin quet: {total_scanned}\n")
        f.write(f"Tong so tin lay:  {len(accepted_details)}\n")
        f.write("="*60 + "\n\n")
        
        for idx, item in enumerate(accepted_details, 1):
            f.write(f"{idx}. [{item['source']}] {item['title']}\n")
            
    print(f"\n✅ Da xuat danh sach {len(accepted_details)} tin ra file 'crawled_news_list.txt'.")
    print("-" * 60)
    
    print("\n✅ ACCEPTED DISASTER NEWS (What made it through):")
    if not accepted_details:
        print("   (No disaster news found at this exact moment)")
    else:
        for item in accepted_details:
            print(f" + [{item['source']}] {item['title']}")
            
    print("\n❌ REJECTED NOISE SAMPLES (What was filtered out):")
    for item in rejected_samples[:15]: # Show top 15 noise examples
        print(f" - [{item['source']}] {item['title']}")
        
    print("\nDone.")

async def fetch_and_process(client, source_name, url, method):
    res = {"total": 0, "accepted": 0, "accepted_items": [], "rejected_items": []}
    try:
        resp = await client.get(url)
        if resp.status_code != 200: return res
        
        feed = feedparser.parse(resp.text)
        res["total"] = len(feed.entries)
        
        for entry in feed.entries:
            title = entry.get("title", "")
            title = html.unescape(title)
            desc = entry.get("summary", "") or entry.get("description", "")
            desc = html.unescape(desc)
            # Combine for NLP check
            full_text = f"{title}\n{desc}"
            
            # === THE NLP FILTER ===
            # trusted_source=False to be strict
            is_valid = nlp.contains_disaster_keywords(full_text, trusted_source=False)
            
            item = {"source": source_name, "title": title}
            if is_valid:
                res["accepted"] += 1
                res["accepted_items"].append(item)
            else:
                res["rejected_items"].append(item)
                
    except Exception:
        pass
    
    return res

if __name__ == "__main__":
    asyncio.run(dry_run())
