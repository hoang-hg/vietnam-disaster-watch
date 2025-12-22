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

    async def scrape_kttv_portal(self, domain: str) -> List[dict]:
        """Scrape any KTTV portal (National or Provincial) - Targeted Scrape."""
        if not _HAS_BS4: return []

        # Build start URL based on domain
        if "thoitietvietnam" in domain:
            url = f"https://www.thoitietvietnam.gov.vn/kttv/"
        elif domain.startswith("http"):
            url = domain
        else:
            url = f"https://{domain}/kttv/" if "kttv.gov.vn" in domain and domain != "kttv.gov.vn" else f"https://{domain}"

        response = await self._get_with_retry(url)
        if not response:
            # Try standard /kttv/ path if root fails
            if not url.endswith("/kttv/"):
                url_alt = url.rstrip("/") + "/kttv/"
                response = await self._get_with_retry(url_alt)
            
            if not response:
                # Fallback to nchmf for national domain
                if "thoitietvietnam" in domain or "nchmf" in domain:
                    url = "https://nchmf.gov.vn/kttv/"
                    response = await self._get_with_retry(url)
                
                if not response: return []

        response.encoding = "utf-8"
        articles = []
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Provincial sites often have news in these containers
            content_containers = soup.find_all(['ul', 'div'], class_=re.compile(r'list-news|uk-list|news-list|tin-tuc|lastest-news', re.I))
            
            seen_titles = set()
            all_links = []
            
            if content_containers:
                for container in content_containers:
                    all_links.extend(container.find_all('a', href=True))
            
            # If no containers found, try all links
            if not all_links:
                all_links = soup.find_all('a', href=True)

            base_domain = domain if not domain.startswith("www.") else domain[4:]

            for link in all_links:
                if len(articles) >= 30:
                    break
                
                href = link.get('href', '').strip()
                title = link.get_text(strip=True)
                
                # If title is empty, check 'title' or 'alt' attribute
                if not title:
                    title = link.get('title', '') or link.get('alt', '')
                
                if not title or len(title) < 15:
                    continue

                # Deduplicate
                if title in seen_titles:
                    continue
                
                # Filter out utility links (contact, login, etc)
                if any(x in href.lower() for x in ['contact', 'login', 'signup', 'feedback', 'search']):
                    continue
                
                # Heuristic for news links in KTTV portals:
                # 1. Contains 'post', 'view', 'detail', 'tin-tuc'
                # 2. Ends with .html or has a numeric ID
                is_news = False
                if any(x in href.lower() for x in ['post', 'view', 'detail', 'tin-tuc', 'news', 'dubao']):
                    is_news = True
                elif re.search(r'/\d+/?$', href) or re.search(r'-\d+\.html', href):
                    is_news = True
                
                if not is_news:
                    continue

                # Fix relative URL
                full_url = href
                if not href.startswith("http"):
                    if href.startswith("/"):
                        full_url = f"https://{domain.rstrip('/')}{href}"
                    else:
                        full_url = f"{url.rstrip('/')}/{href}"

                # Attempt to find summary/description
                summary = ""
                # Strategy: Look inside the same container for p, span, or div with class summary/desc
                parent = link.find_parent(['li', 'div', 'article'])
                if parent:
                    desc_tag = parent.find(['p', 'div', 'span'], class_=re.compile(r'summary|desc|lead|snippet|short', re.I))
                    if desc_tag:
                        summary = desc_tag.get_text(strip=True)
                    else:
                        # Fallback: Look for any p or div that isn't the title link
                        all_p = parent.find_all('p')
                        for p in all_p:
                            p_text = p.get_text(strip=True)
                            if p_text and p_text != title:
                                summary = p_text
                                break

                seen_titles.add(title)
                
                articles.append({
                    "title": title,
                    "url": full_url,
                    "source": domain,
                    "summary": summary,
                    "scraped_at": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.debug(f"Error scraping KTTV portal {domain}: {e}")
        
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
        elif "thoitietvietnam" in domain_lower or "nchmf" in domain_lower or "kttv" in domain_lower:
            return await self.scrape_kttv_portal(domain)
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
