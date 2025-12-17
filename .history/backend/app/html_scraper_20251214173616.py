# -*- coding: utf-8 -*-
"""
HTML scraper module for Vietnamese news websites without RSS feeds.

This module provides fallback scraping capabilities when RSS feeds are unavailable.
It uses BeautifulSoup to extract articles from news listing pages with disaster keyword filtering.
"""

import asyncio
import re
from datetime import datetime
from typing import Optional, List
import httpx
from bs4 import BeautifulSoup
import logging

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
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def scrape_tuoitre(self) -> List[dict]:
        """Scrape Tuổi Trẻ news listing."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://tuoitre.vn/thoi-su",
                    headers=self.headers,
                    follow_redirects=True
                )
                response.encoding = "utf-8"
                return self._extract_tuoitre(response.text)
        except Exception as e:
            logger.error(f"Tuổi Trẻ scrape failed: {e}")
            return []

    def _extract_tuoitre(self, html: str) -> List[dict]:
        """Extract articles from Tuổi Trẻ HTML."""
        articles = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            # Tuổi Trẻ uses article class for news items
            items = soup.find_all("article", class_="box-category-item-common")
            
            for item in items[:20]:  # Limit to 20 per page
                try:
                    a = item.find("a", class_="box-title-link")
                    if not a:
                        continue
                    
                    title = a.get_text(strip=True)
                    if not self._has_disaster_keyword(title):
                        continue
                    
                    url = a.get("href", "").strip()
                    if not url.startswith("http"):
                        url = "https://tuoitre.vn" + url if url.startswith("/") else None
                    
                    if not url:
                        continue
                    
                    # Try to find summary/description
                    summary_elem = item.find("p", class_="box-category-item-sapo")
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    articles.append({
                        "title": title,
                        "url": url,
                        "source": "tuoitre.vn",
                        "summary": summary,
                        "scraped_at": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.debug(f"Error extracting Tuổi Trẻ article: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error parsing Tuổi Trẻ HTML: {e}")
        
        return articles

    async def scrape_vnexpress(self) -> List[dict]:
        """Scrape VnExpress news listing."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://vnexpress.net/thoi-su-trong-ngay",
                    headers=self.headers,
                    follow_redirects=True
                )
                response.encoding = "utf-8"
                return self._extract_vnexpress(response.text)
        except Exception as e:
            logger.error(f"VnExpress scrape failed: {e}")
            return []

    def _extract_vnexpress(self, html: str) -> List[dict]:
        """Extract articles from VnExpress HTML."""
        articles = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            # VnExpress uses article tag with class
            items = soup.find_all("article", class_="item-news")
            
            for item in items[:20]:
                try:
                    a = item.find("a", class_="title-news")
                    if not a:
                        continue
                    
                    title = a.get_text(strip=True)
                    if not self._has_disaster_keyword(title):
                        continue
                    
                    url = a.get("href", "").strip()
                    if not url.startswith("http"):
                        url = "https://vnexpress.net" + url if url.startswith("/") else None
                    
                    if not url:
                        continue
                    
                    summary_elem = item.find("p", class_="description")
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    articles.append({
                        "title": title,
                        "url": url,
                        "source": "vnexpress.net",
                        "summary": summary,
                        "scraped_at": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.debug(f"Error extracting VnExpress article: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error parsing VnExpress HTML: {e}")
        
        return articles

    async def scrape_dantri(self) -> List[dict]:
        """Scrape Dân Trí news listing."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://dantri.com.vn/thoi-su.htm",
                    headers=self.headers,
                    follow_redirects=True
                )
                response.encoding = "utf-8"
                return self._extract_dantri(response.text)
        except Exception as e:
            logger.error(f"Dân Trí scrape failed: {e}")
            return []

    def _extract_dantri(self, html: str) -> List[dict]:
        """Extract articles from Dân Trí HTML."""
        articles = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            # Dân Trí uses article elements
            items = soup.find_all("article")
            
            for item in items[:20]:
                try:
                    a = item.find("a")
                    if not a:
                        continue
                    
                    title = a.get_text(strip=True)
                    if not self._has_disaster_keyword(title) or len(title) < 10:
                        continue
                    
                    url = a.get("href", "").strip()
                    if not url.startswith("http"):
                        url = "https://dantri.com.vn" + url if url.startswith("/") else None
                    
                    if not url:
                        continue
                    
                    summary_elem = item.find("p")
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    articles.append({
                        "title": title,
                        "url": url,
                        "source": "dantri.com.vn",
                        "summary": summary,
                        "scraped_at": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.debug(f"Error extracting Dân Trí article: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error parsing Dân Trí HTML: {e}")
        
        return articles

    async def scrape_source(self, domain: str) -> List[dict]:
        """Route to appropriate scraper based on domain."""
        domain_lower = domain.lower()
        
        if "tuoitre" in domain_lower:
            return await self.scrape_tuoitre()
        elif "vnexpress" in domain_lower:
            return await self.scrape_vnexpress()
        elif "dantri" in domain_lower:
            return await self.scrape_dantri()
        else:
            logger.warning(f"No scraper implemented for {domain}")
            return []

    def _has_disaster_keyword(self, text: str) -> bool:
        """Check if text contains disaster-related keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in DISASTER_KEYWORDS)

    async def scrape_all_available(self) -> dict:
        """Scrape all implemented sources concurrently."""
        results = {
            "tuoitre.vn": await self.scrape_tuoitre(),
            "vnexpress.net": await self.scrape_vnexpress(),
            "dantri.com.vn": await self.scrape_dantri(),
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
