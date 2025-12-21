
import asyncio
import sys
from pathlib import Path
import logging

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

from app.html_scraper import HTMLScraper
from app.sources import build_gnews_rss
import feedparser
import httpx

logging.basicConfig(level=logging.INFO)

async def test_scrapers_and_gnews():
    print("="*60)
    print("TEST: HTML SCRAPER & GNEWS FALLBACK")
    print("="*60)

    # 1. Test HTML Scraper (Thuy Van)
    print("\n1. Testing HTMLScraper for thoitietvietnam.gov.vn...")
    scraper = HTMLScraper()
    # Explicitly call the method we added
    try:
        articles = await scraper.scrape_thoitietvietnam()
        if articles:
            print(f"   [OK] Found {len(articles)} articles from thoitietvietnam.gov.vn")
            for a in articles[:3]:
                print(f"      - {a['title']}")
                print(f"        {a['url']}")
        else:
            print("   [FAIL] No articles found via scrape_thoitietvietnam")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 2. Test GNews Fallback Link Generation & Fetching
    # for a difficult source like baotainguyenmoitruong.vn
    target_domain = "baotainguyenmoitruong.vn"
    print(f"\n2. Testing GNews Fallback for {target_domain}...")
    
    # Generate GNews URL
    gnews_url = build_gnews_rss(target_domain)
    print(f"   Generated URL: {gnews_url[:100]}...")

    # Fetch it
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        try:
            resp = await client.get(gnews_url)
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                print(f"   [OK] Feed contains {len(feed.entries)} entries")
                if len(feed.entries) > 0:
                    for e in feed.entries[:3]:
                        print(f"      - {e.title}")
                        print(f"        {e.link}")
                else:
                    print("   [WARN] 0 entries found in GNews feed")
            else:
                print("   [FAIL] HTTP Error fetching GNews")
        except Exception as e:
            print(f"   [ERROR] Fetch failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrapers_and_gnews())
