import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy.engine import Engine
from sqlalchemy import event

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.html_scraper import HTMLScraper
from app.database import SessionLocal
from app.models import Article
from app.nlp import classify_disaster

async def test_kttv_fetch():
    print("--- STARTING TARGETED KTTV TEST ---")
    scraper = HTMLScraper()
    
    # 1. Fetch
    print("Fetching articles from KTTV...")
    articles = await scraper.scrape_thoitietvietnam()
    print(f"Found {len(articles)} raw articles.")
    
    if not articles:
        print("FAIL: No articles found. Check network or regex.")
        return

    # 2. Check content of first 5
    print("\nSAMPLE ARTICLES:")
    for i, art in enumerate(articles[:5]):
        print(f"[{i+1}] {art['title']}")
        print(f"    URL: {art['url']}")
        
    # 3. Test saving to DB (Dry run logic)
    print("\nCHECKING DATABASE STATUS:")
    db = SessionLocal()
    new_found = 0
    
    for art in articles:
        # Check if exists
        exists = db.query(Article).filter(Article.url == art['url']).first()
        if exists:
            print(f"[EXISTS] {art['title'][:30]}...")
        else:
            print(f"[NEW] >>> {art['title'][:30]}...")
            # Simulate classification
            content = art['title']
            disaster_info = classify_disaster(content)
            
            if disaster_info:
                print(f"    -> CLASSIFIED AS: {disaster_info['primary_type']} (Level: {disaster_info.get('primary_level')}, Hazards: {[h['type'] for h in disaster_info.get('all_hazards', [])]})")
                new_found += 1
            else:
                print(f"    -> IGNORED (Not disaster)")
                
    print(f"\nSummary: {new_found} new valid articles found locally.")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(test_kttv_fetch())
