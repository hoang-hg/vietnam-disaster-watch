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
from .settings import settings
import random
import re

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

# 8 Standardized Disaster Groups (Matching nlp.py)
DISASTER_RULES = [
    ("storm", [r"(?<!\w)bão(?!\w)", r"bão\s*số", r"siêu\s*bão", r"áp\s*thấp", r"ATNĐ", r"áp\s*thấp\s*nhiệt\s*đới"]),
    ("flood_landslide", [r"mưa\s*lũ", r"(?<!\w)lũ(?!\w)", r"(?<!\w)lụt(?!\w)", r"ngập\s*lụt", r"ngập\s*sâu", r"lũ\s*quét", r"lũ\s*ống", r"sạt\s*lở", r"lở\s*đất", r"sụt\s*lún"]),
    ("heat_drought", [r"nắng\s*nóng", r"hạn\s*hán", r"khô\s*hạn", r"xâm\s*nhập\s*mặn", r"nhiễm\s*mặn", r"độ\s*mặn"]),
    ("wind_fog", [r"gió\s*mạnh", r"gió\s*giật", r"biển\s*động", r"sóng\s*lớn", r"sương\s*mù"]),
    ("storm_surge", [r"triều\s*cường", r"nước\s*dâng", r"nước\s*biển\s*dâng"]),
    ("extreme_other", [r"dông\s*lốc", r"lốc", r"lốc\s*xoáy", r"mưa\s*đá", r"sét", r"rét\s*hại", r"rét\s*đậm", r"băng\s*giá", r"sương\s*muối"]),
    ("wildfire", [r"cháy\s*rừng", r"nguy\s*cơ\s*cháy\s*rừng"]),
    ("quake_tsunami", [r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn", r"nứt\s*đất", r"sóng\s*thần"]),
]

DISASTER_NEGATIVE = [
    r"bão\s*(?:giá|sale|like|scandal|lòng|đơn|quà|tài\s*chính)",
    r"cháy\s*(?:hàng|túi|phim|vé|nhà|xe|chung\s*cư|xưởng|kho)",
    r"ngập(?:\s*tràn|\s*trong\s*nợ|\s*nợ)",
    r"\btăng\s*lương\b", r"\bbắt\s*giữ\b", r"\blừa\s*đảo\b", r"\bsập\s*bẫy\b"
]

def contains_disaster_keywords(text: str) -> bool:
    """Check if text contains disaster keywords using regex patterns."""
    t = text.lower()
    
    # First check negative veto
    for p in DISASTER_NEGATIVE:
        if re.search(p, t, flags=re.IGNORECASE):
            return False
            
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
        # Default fallback if settings fail
        self.default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    async def _get_with_retry(self, url: str) -> Optional[httpx.Response]:
        """Fetch URL with retries, random User-Agent, and exponential backoff."""
        transport = httpx.AsyncHTTPTransport(retries=3)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=transport) as client:
            for attempt in range(3):
                try:
                    # Select random UA
                    ua = random.choice(settings.user_agents) if hasattr(settings, 'user_agents') and settings.user_agents else self.default_ua
                    headers = {"User-Agent": ua}
                    
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response
                except httpx.HTTPError as e:
                    if attempt == 2:
                        logger.debug(f"Failed to fetch {url} after 3 attempts: {e}")
                        return None
                    await asyncio.sleep(1 * (attempt + 1))
                except Exception as e:
                    logger.debug(f"Unexpected error fetching {url}: {e}")
                    return None
        return None

    async def scrape_tuoitre(self) -> List[dict]:
        """Scrape Tuổi Trẻ news listing - fallback only."""
        if not _HAS_BS4: return []
        
        response = await self._get_with_retry("https://tuoitre.vn/")
        if not response: return []
        
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "tuoitre.vn", max_items=15)

    async def scrape_vnexpress(self) -> List[dict]:
        """Scrape VnExpress news listing - fallback only."""
        if not _HAS_BS4: return []
        
        response = await self._get_with_retry("https://vnexpress.net/")
        if not response: return []
        
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "vnexpress.net", max_items=15)

    async def scrape_dantri(self) -> List[dict]:
        """Scrape Dân Trí news listing - fallback only."""
        if not _HAS_BS4: return []
        
        response = await self._get_with_retry("https://dantri.com.vn/")
        if not response: return []
        
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "dantri.com.vn", max_items=15)

    async def scrape_nld(self) -> List[dict]:
        """Scrape Người Lao Động news listing - fallback only."""
        if not _HAS_BS4: return []
        
        response = await self._get_with_retry("https://nld.com.vn/")
        if not response: return []
        
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "nld.com.vn", max_items=15)

    async def scrape_sggp(self) -> List[dict]:
        """Scrape SGGP news listing - fallback only."""
        if not _HAS_BS4: return []
        
        response = await self._get_with_retry("https://sggp.org.vn/")
        if not response: return []
        
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "sggp.org.vn", max_items=15)

    async def scrape_thoitietvietnam(self) -> List[dict]:
        """Scrape Thoi Tiet Vietnam (KTTV) - Targeted Scrape."""
        if not _HAS_BS4: return []

        # Target valid news page on the new official domain
        url = "https://www.thoitietvietnam.gov.vn/kttv/" 
        response = await self._get_with_retry(url)
        if not response: 
            # Try alternative old domain if first fails
            url = "https://nchmf.gov.vn/kttv/"
            response = await self._get_with_retry(url)
            if not response: return []

        response.encoding = "utf-8"
        articles = []
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # The list of news is usually in a specific container, but generic 'a' search works if we filter by URL pattern
            # The links look like /kttv/vi-VN/1/title-postID.html
            all_links = soup.find_all('a', href=True)
            
            seen_titles = set()
            for link in all_links:
                if len(articles) >= 20:
                    break
                
                href = link.get('href', '').strip()
                # Specific pattern for news posts on this site
                if "post" not in href:
                    continue
                
                # Fix relative URL
                if href.startswith("/"):
                    full_url = "https://www.thoitietvietnam.gov.vn" + href
                elif not href.startswith("http"):
                    # relative without slash?
                    full_url = "https://www.thoitietvietnam.gov.vn/kttv/" + href
                else:
                    full_url = href

                title = link.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                # Deduplicate
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # For this TRUSTED source, we DO NOT filter by disaster keywords here.
                # We let the crawler/NLP pipeline decide, or we accept all because it is a specialized source.
                
                articles.append({
                    "title": title,
                    "url": full_url,
                    "source": "thoitietvietnam.gov.vn",
                    "summary": "",
                    "scraped_at": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.debug(f"Error scraping KTTV: {e}")
        
        return articles



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
        elif "thoitietvietnam" in domain_lower or "nchmf" in domain_lower:
            return await self.scrape_thoitietvietnam()
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
                    if len(title) < 20 or len(title) > 500:
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

def fetch_article_full_text(url: str, timeout: int = 15) -> Optional[str]:
    """
    Synchronous wrapper for fetching full article text, suitable for usage in crawler loop.
    Extracts the main body text, ignoring nav, footer, etc.
    """
    if not _HAS_BS4: return None
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove scripts, styles, etc.
            for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
                s.decompose()
            
            # Common article selectors for VN news sites
            # Tuoi Tre, VNExpress, Thanh Nien, etc.
            content_tags = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'content|body|detail|post-content|article-content', re.I))
            
            if content_tags:
                # Get the biggest one
                main_content = max(content_tags, key=lambda x: len(x.get_text()))
                return main_content.get_text(separator=' ', strip=True)
            
            # Fallback to body text
            return soup.body.get_text(separator=' ', strip=True) if soup.body else soup.get_text(separator=' ', strip=True)
            
    except Exception as e:
        logger.error(f"Error fetching full text from {url}: {e}")
        return None


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
