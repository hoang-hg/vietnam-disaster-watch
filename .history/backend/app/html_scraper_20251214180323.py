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
import re

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

logger = logging.getLogger(__name__)

# Build disaster keyword patterns (matching nlp.py DISASTER_RULES)
DISASTER_RULES = [
    ("earthquake", [r"\bđộng\s*đất\b", r"\brung\s*chấn\b", r"\bdự\s*chấn\b", r"\bnứt\s*đất\b", r"\bđứt\s*gãy\b"]),
    ("tsunami", [r"\bsóng\s*thần\b", r"\bcảnh\s*báo\s*sóng\s*thần\b"]),
    ("landslide", [r"\bsạt\s*lở\b", r"\blở\s*đất\b", r"\btrượt\s*đất\b", r"\btaluy\b", r"\bsạt\s*taluy\b", r"\bsạt\s*lở\s*bờ\b", r"\bsụt\s*lún\b"]),
    ("flood", [r"\bmưa\s*lũ\b", r"\blũ\b", r"\blụt\b", r"\bngập\s*lụt\b", r"\bngập\s*sâu\b", r"\blũ\s*quét\b", r"\blũ\s*ống\b", r"\btriều\s*cường\b", r"\bnước\s*dâng\b"]),
    ("storm", [r"\bbão\b", r"\bbão\s*số\b", r"\bsiêu\s*bão\b", r"\báp\s*thấp\b", r"\bATNĐ\b", r"\báp\s*thấp\s*nhiệt\s*đới\b"]),
    ("wind_hail", [r"\bgió\s*mạnh\b", r"\bgió\s*giật\b", r"\bdông\s*lốc\b", r"\blốc\b", r"\blốc\s*xoáy\b", r"\bvòi\s*rồng\b", r"\bmưa\s*đá\b", r"\bgiông\s*sét\b", r"\bsét\b"]),
    ("wildfire", [r"\bcháy\s*rừng\b", r"\bnguy\s*cơ\s*cháy\s*rừng\b"]),
    ("extreme_weather", [r"\bnắng\s*nóng\b", r"\bnắng\s*nóng\s*gay\s*gắt\b", r"\bhạn\s*hán\b", r"\bkhô\s*hạn\b", r"\brét\s*đậm\b", r"\brét\s*hại\b", r"\bbăng\s*giá\b", r"\bxâm\s*nhập\s*mặn\b"]),
]

def contains_disaster_keywords(text: str) -> bool:
    """Check if text contains disaster keywords using regex patterns."""
    t = text.lower()
    for label, patterns in DISASTER_RULES:
        for p in patterns:
            if re.search(p, t, flags=re.IGNORECASE):
                return True
    return False

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
        return contains_disaster_keywords(text)

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
