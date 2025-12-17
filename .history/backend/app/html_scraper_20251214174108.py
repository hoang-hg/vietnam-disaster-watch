# -*- coding: utf-8 -*-
"""
HTML scraper module for Vietnamese news websites without RSS feeds.

This module provides fallback scraping capabilities when RSS feeds are unavailable.
It extracts articles from news listing pages with disaster keyword filtering.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, List
import httpx
import logging

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

logger = logging.getLogger(__name__)

# Disaster-related keywords to filter news articles
DISASTER_KEYWORDS = [
    "lũ", "lụt", "ngập", "sạt", "núi", "lở",
    "bão", "tâm bão", "gió giật", "sóng",
    "động đất", "dư chấn",
    "nóng", "hạn", "khô",
    "cảnh báo", "nguy hiểm", "cấp cứu",
    "thiệt hại", "nạn nhân", "chết", "mất tích",
    "ứng cứu", "giải cứu", "cứu hộ",
    "tây nguyên", "miền bắc", "miền trung", "miền nam",
    "hà nội", "hcm", "đà nẵng", "huế"
]

class HTMLScraper:
    """Scrapes news articles from websites without RSS feeds."""

    def __init__(self, timeout: int = 10):
        if not _HAS_BS4:
            logger.warning("BeautifulSoup4 not available - HTML scraping disabled")
        
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def scrape_tuoitre(self) -> List[dict]:
        """Scrape Tuổi Trẻ news listing - fallback only."""
        if not _HAS_BS4:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get("https://tuoitre.vn/", follow_redirects=True)
                response.encoding = "utf-8"
                return self._extract_generic_links(response.text, "tuoitre.vn", max_items=15)
        except Exception as e:
            logger.debug(f"Tuổi Trẻ scrape failed: {e}")
            return []

    async def scrape_vnexpress(self) -> List[dict]:
        """Scrape VnExpress news listing - fallback only."""
        if not _HAS_BS4:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get("https://vnexpress.net/", follow_redirects=True)
                response.encoding = "utf-8"
                return self._extract_generic_links(response.text, "vnexpress.net", max_items=15)
        except Exception as e:
            logger.debug(f"VnExpress scrape failed: {e}")
            return []

    async def scrape_dantri(self) -> List[dict]:
        """Scrape Dân Trí news listing - fallback only."""
        if not _HAS_BS4:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get("https://dantri.com.vn/", follow_redirects=True)
                response.encoding = "utf-8"
                return self._extract_generic_links(response.text, "dantri.com.vn", max_items=15)
        except Exception as e:
            logger.debug(f"Dân Trí scrape failed: {e}")
            return []

    async def scrape_nld(self) -> List[dict]:
        """Scrape Người Lao Động news listing - fallback only."""
        if not _HAS_BS4:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get("https://nld.com.vn/", follow_redirects=True)
                response.encoding = "utf-8"
                return self._extract_generic_links(response.text, "nld.com.vn", max_items=15)
        except Exception as e:
            logger.debug(f"Người Lao Động scrape failed: {e}")
            return []

    async def scrape_sggp(self) -> List[dict]:
        """Scrape SGGP news listing - fallback only."""
        if not _HAS_BS4:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get("https://sggp.org.vn/", follow_redirects=True)
                response.encoding = "utf-8"
                return self._extract_generic_links(response.text, "sggp.org.vn", max_items=15)
        except Exception as e:
            logger.debug(f"SGGP scrape failed: {e}")
            return []

    async def scrape_source(self, domain: str) -> List[dict]:
        """Route to appropriate scraper based on domain."""
        if not _HAS_BS4:
            logger.warning(f"BeautifulSoup4 not available - cannot scrape {domain}")
            return []
        
        domain_lower = domain.lower()
        
        if "tuoitre" in domain_lower:
            return await self.scrape_tuoitre()
        elif "vnexpress" in domain_lower:
            return await self.scrape_vnexpress()
        elif "dantri" in domain_lower:
            return await self.scrape_dantri()
        elif "nld" in domain_lower:
            return await self.scrape_nld()
        elif "sggp" in domain_lower:
            return await self.scrape_sggp()
        else:
            logger.debug(f"No scraper implemented for {domain}")
            return []

    def _has_disaster_keyword(self, text: str) -> bool:
        """Check if text contains disaster-related keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in DISASTER_KEYWORDS)

    def _extract_generic_links(self, html: str, domain: str, max_items: int = 15) -> List[dict]:
        """Extract links from generic HTML using minimal assumptions."""
        articles = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            all_links = soup.find_all('a', href=True)
            
            seen_titles = set()
            for link in all_links:
                if len(articles) >= max_items:
                    break
                
                try:
                    title = link.get_text(strip=True)
                    
                    # Filter by length and keyword
                    if len(title) < 20 or len(title) > 200:
                        continue
                    if title in seen_titles:
                        continue
                    if not self._has_disaster_keyword(title):
                        continue
                    
                    url = link.get('href', '').strip()
                    
                    # Ensure absolute URL
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = f'https://{domain}' + url
                    elif not url.startswith('http'):
                        continue
                    
                    seen_titles.add(title)
                    articles.append({
                        "title": title,
                        "url": url,
                        "source": domain,
                        "summary": "",
                        "scraped_at": datetime.utcnow().isoformat()
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error parsing HTML for {domain}: {e}")
        
        return articles

    async def scrape_all_available(self) -> dict:
        """Scrape all implemented sources concurrently."""
        if not _HAS_BS4:
            logger.warning("HTML scraping disabled - BeautifulSoup4 not available")
            return {}
        
        results = {
            "tuoitre.vn": await self.scrape_tuoitre(),
            "vnexpress.net": await self.scrape_vnexpress(),
            "dantri.com.vn": await self.scrape_dantri(),
            "nld.com.vn": await self.scrape_nld(),
            "sggp.org.vn": await self.scrape_sggp(),
        }
        return results


# Simple test function
async def test_scraper():
    """Test the HTML scraper."""
    scraper = HTMLScraper()
    print("Testing HTML scraper...")
    
    results = await scraper.scrape_all_available()
    for source, articles in results.items():
        print(f"\n{source}: {len(articles)} articles found")
        for article in articles[:3]:
            print(f"  - {article['title'][:70]}...")


if __name__ == "__main__":
    asyncio.run(test_scraper())
