
import asyncio
import sys
from pathlib import Path
import logging

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

from app.html_scraper import HTMLScraper
import logging

# Set logging to see debug info
logging.basicConfig(level=logging.INFO)

async def test_baotainguyen_scraper():
    print("="*60)
    print("TEST: HTML SCRAPER FOR TAINGUYENMOITRUONG")
    print("="*60)

    scraper = HTMLScraper()
    print("Fetching articles from baotainguyenmoitruong.vn...")
    
    try:
        articles = await scraper.scrape_baotainguyenmoitruong()
        
        if articles:
            print(f"\n[SUCCESS] Found {len(articles)} articles!")
            print("-" * 50)
            for i, a in enumerate(articles[:5], 1):
                print(f"{i}. {a['title']}")
                print(f"   URL: {a['url']}")
            print("-" * 50)
            
            # Check if any article looks like disaster news
            disaster_count = 0
            keywords = ['bão', 'lũ', 'mưa', 'sạt lở', 'hạn hán', 'nắng nóng']
            for a in articles:
                t = a['title'].lower()
                if any(k in t for k in keywords):
                    disaster_count += 1
            
            print(f"Disaster-related articles found: {disaster_count}/{len(articles)}")
                
        else:
            print("\n[FAIL] No articles found via scraper.")
            
    except Exception as e:
        print(f"\n[ERROR] Exception occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_baotainguyen_scraper())
