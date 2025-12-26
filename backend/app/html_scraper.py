# -*- coding: utf-8 -*-
"""
HTML scraper module for Vietnamese news websites without RSS feeds.

This module provides fallback scraping capabilities when RSS feeds are unavailable.
It extracts articles from news listing pages with disaster keyword filtering.
"""

import asyncio
import time
from datetime import datetime, timezone
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

# Import Standardized Disaster Groups and Negative Patterns from nlp.py
from .nlp import DISASTER_RULES as NLP_DISASTER_RULES, DISASTER_NEGATIVE as NLP_DISASTER_NEGATIVE

# Convert NLP_DISASTER_RULES (tuple list) to simple regex list for internal keyword check if needed
# or just use the rules directly.
DISASTER_RULES = NLP_DISASTER_RULES
DISASTER_NEGATIVE = NLP_DISASTER_NEGATIVE

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
    
    _shared_client: Optional[httpx.AsyncClient] = None

    def __init__(self, timeout: int = 15):
        if not _HAS_BS4:
            logger.warning("BeautifulSoup4 not available - HTML scraping disabled")
        
        self.timeout = timeout
        self.default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create singleton httpx client for connection pooling."""
        if HTMLScraper._shared_client is None or HTMLScraper._shared_client.is_closed:
            limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
            HTMLScraper._shared_client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                limits=limits,
                headers={"User-Agent": self.default_ua}
            )
        return HTMLScraper._shared_client

    async def _get_with_retry(self, url: str) -> Optional[httpx.Response]:
        """Fetch URL with retries, random User-Agent, and exponential backoff."""
        client = await self.get_client()
        for attempt in range(3):
            try:
                # Select random UA if available
                ua = random.choice(settings.user_agents) if hasattr(settings, 'user_agents') and settings.user_agents else self.default_ua
                headers = {"User-Agent": ua}
                
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                if attempt == 2:
                    logger.debug(f"Failed to fetch {url} after 3 attempts: {e}")
                    return None
                await asyncio.sleep(0.5 * (attempt + 1)) # Reduced backoff for performance
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

    async def scrape_thanhnien(self) -> List[dict]:
        """Scrape Thanh Niên news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://thanhnien.vn/thoi-su.htm")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "thanhnien.vn", max_items=15)

    async def scrape_vietnamnet(self) -> List[dict]:
        """Scrape VietNamNet news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://vietnamnet.vn/thoi-su")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "vietnamnet.vn", max_items=15)

    async def scrape_laodong(self) -> List[dict]:
        """Scrape Lao Động news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://laodong.vn/thoi-su")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "laodong.vn", max_items=15)

    async def scrape_nhandan(self) -> List[dict]:
        """Scrape Nhân Dân news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://nhandan.vn/xa-hoi")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "nhandan.vn", max_items=15)

    async def scrape_tienphong(self) -> List[dict]:
        """Scrape Tiền Phong news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://tienphong.vn/xa-hoi")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "tienphong.vn", max_items=15)

    async def scrape_baotintuc(self) -> List[dict]:
        """Scrape Báo Tin Tức news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://baotintuc.vn/thoi-su.htm")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "baotintuc.vn", max_items=15)

    async def scrape_vtv(self) -> List[dict]:
        """Scrape VTV News news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://vtv.vn/xa-hoi.htm")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "vtv.vn", max_items=15)

    async def scrape_vov(self) -> List[dict]:
        """Scrape VOV (Voice of Vietnam) news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://vov.vn/xa-hoi")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "vov.vn", max_items=15)

    async def scrape_vietnamplus(self) -> List[dict]:
        """Scrape VietnamPlus news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://www.vietnamplus.vn/xa-hoi/")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "vietnamplus.vn", max_items=15)

    async def scrape_vietnamvn(self) -> List[dict]:
        """Scrape Vietnam.vn (Official Portal)."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://www.vietnam.vn/category/xa-hoi/")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "vietnam.vn", max_items=15)

    async def scrape_vtcnews(self) -> List[dict]:
        """Scrape VTC News news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://vtcnews.vn/thoi-su")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "vtcnews.vn", max_items=15)

    async def scrape_bnews(self) -> List[dict]:
        """Scrape Bnews (VNA branch) news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://bnews.vn/thoi-su/50.html")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "bnews.vn", max_items=15)

    async def scrape_suckhoedoisong(self) -> List[dict]:
        """Scrape Báo Sức khỏe & Đời sống news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://suckhoedoisong.vn/thoi-su.htm")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "suckhoedoisong.vn", max_items=15)

    async def scrape_monre_news(self) -> List[dict]:
        """Scrape Báo Tài nguyên & Môi trường news listing."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry("https://baotainguyenmoitruong.vn/thoi-su")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, "baotainguyenmoitruong.vn", max_items=15)

    async def scrape_generic(self, domain: str) -> List[dict]:
        """Generic fallback scraper for any domain."""
        if not _HAS_BS4: return []
        response = await self._get_with_retry(f"https://{domain}/")
        if not response: return []
        response.encoding = "utf-8"
        return self._extract_generic_links(response.text, domain, max_items=15)

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
                    "scraped_at": datetime.now(timezone.utc).isoformat()
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
        elif "thanhnien" in domain_lower:
            return await self.scrape_thanhnien()
        elif "vietnamnet" in domain_lower:
            return await self.scrape_vietnamnet()
        elif "laodong" in domain_lower:
            return await self.scrape_laodong()
        elif "nhandan" in domain_lower:
            return await self.scrape_nhandan()
        elif "tienphong" in domain_lower:
            return await self.scrape_tienphong()
        elif "baotintuc" in domain_lower:
            return await self.scrape_baotintuc()
        elif "vtv" in domain_lower:
            return await self.scrape_vtv()
        elif "vov" in domain_lower:
            return await self.scrape_vov()
        elif "vietnamplus" in domain_lower:
            return await self.scrape_vietnamplus()
        elif "vietnam.vn" in domain_lower:
            return await self.scrape_vietnamvn()
        elif "vtcnews" in domain_lower:
            return await self.scrape_vtcnews()
        elif "bnews" in domain_lower:
            return await self.scrape_bnews()
        elif "suckhoedoisong" in domain_lower:
            return await self.scrape_suckhoedoisong()
        elif "baotainguyenmoitruong" in domain_lower:
            return await self.scrape_monre_news()
        elif any(x in domain_lower for x in ["gov.vn", "nchmf.gov.vn", "thoitietvietnam.gov.vn", "phongchongthientai.mard.gov.vn", "dyke.gov.vn", "mrcc.gov.vn", "vinasar.gov.vn"]):
            return await self.scrape_kttv_portal(domain)
        else:
            return await self.scrape_generic(domain)

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
                        "scraped_at": datetime.now(timezone.utc).isoformat()
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
        
        results_list = await asyncio.gather(
            self.scrape_tuoitre(),
            self.scrape_vnexpress(),
            self.scrape_dantri(),
            self.scrape_nld(),
            self.scrape_sggp(),
            self.scrape_thanhnien(),
            self.scrape_vietnamnet(),
            self.scrape_vtv(),
            self.scrape_vov(),
            self.scrape_vietnamplus(),
            self.scrape_vietnamvn(),
            self.scrape_vtcnews(),
            self.scrape_bnews(),
            self.scrape_laodong(),
            self.scrape_nhandan(),
            self.scrape_tienphong(),
            self.scrape_baotintuc(),
            self.scrape_kttv_portal("thoitietvietnam.gov.vn"),
            return_exceptions=True
        )
        
        keys = [
            "tuoitre.vn", "vnexpress.net", "dantri.com.vn", "nld.com.vn", "sggp.org.vn", 
            "thanhnien.vn", "vietnamnet.vn", "vtv.vn", "vov.vn", "vietnamplus.vn",
            "vietnam.vn", "vtcnews.vn", "bnews.vn", "laodong.vn", "nhandan.vn", "tienphong.vn",
            "baotintuc.vn", "thoitietvietnam.gov.vn"
        ]
        results = {}
        for i, key in enumerate(keys):
            if isinstance(results_list[i], list):
                results[key] = results_list[i]
            else:
                logger.error(f"Error scraping {key}: {results_list[i]}")
                results[key] = []
        return results

def decode_gnews_url(url: str) -> str:
    """
    Decodes a Google News redirect URL to extract the original article URL.
    Handles the newer nested Protobuf-like binary format.
    """
    if "news.google.com/rss/articles/" not in url:
        return url
    
    try:
        encoded_part = url.split("articles/")[1].split("?")[0]
        
        import base64
        padding = (4 - len(encoded_part) % 4) % 4
        encoded_part += "=" * padding
        
        # Original binary protobuf
        decoded = base64.urlsafe_b64decode(encoded_part)
        
        # Strategy 1: UTF-8 scan for http
        content = decoded.decode('utf-8', errors='ignore')
        match = re.search(r'https?://[^\x00-\x1f\x7f-\xff]+', content)
        if match:
            extracted_url = match.group(0)
            clean_url = re.split(r'[\?\"\'\s\x00]', extracted_url)[0]
            if "." in clean_url and len(clean_url) > 10:
                return clean_url
        
        # Strategy 2: Greedy search for known news domains (for when bits are scrambled)
        # This works if the URL is plain but preceded by binary headers.
        domains = [".vn", ".com.vn", ".net.vn", ".org.vn", ".gov.vn", ".net", ".edu.vn"]
        for dom in domains:
            idx = decoded.find(dom.encode())
            if idx != -1:
                # Found the domain! Now backtrack to find 'http' or start of path
                start = decoded.rfind(b"http", 0, idx)
                if start != -1:
                    # Found http, extract until next binary junk
                    end = idx + len(dom)
                    # Extend end to catch the path
                    while end < len(decoded) and (33 <= decoded[end] <= 126):
                        end += 1
                    extracted = decoded[start:end].decode('utf-8', errors='ignore')
                    if "." in extracted:
                        return extracted
                else:
                    # Only found domain, try to extract surrounding printable chars
                    # (Useful for path-only or root matches)
                    start = idx
                    while start > 0 and (33 <= decoded[start-1] <= 126):
                        start -= 1
                    end = idx + len(dom)
                    while end < len(decoded) and (33 <= decoded[end] <= 126):
                        end += 1
                    extracted = decoded[start:end].decode('utf-8', errors='ignore')
                    if extracted.startswith(("http", "www")):
                        if not extracted.startswith("http"): extracted = "https://" + extracted
                        return extracted

    except Exception:
        pass
        
    return url

async def fetch_article_full_text_async(url: str, timeout: int = 15) -> Optional[dict]:
    """
    Asynchronous version of fetch_article_full_text.
    Returns a dict with 'text', 'images', 'final_url', and 'is_broken'.
    """
    if not _HAS_BS4: return None
    
    # 0. Decode Google News URL if possible
    decoded_url = decode_gnews_url(url)
    is_gnews = (decoded_url == url and "news.google.com" in url)
    url = decoded_url
    
    # Use a very browser-like header set
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        scraper = HTMLScraper(timeout=timeout)
        client = await scraper.get_client()
        
        resp = await client.get(url, follow_redirects=True, headers=headers)
        resp.raise_for_status()
            
        final_url = str(resp.url)
        
        # Smart encoding detection
        if resp.encoding == 'ISO-8859-1' or not resp.encoding:
            resp.encoding = resp.apparent_encoding
        
        html_content = resp.text
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. Image Extraction
        images = []
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            images.append(og_img["content"])
        
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if any(x in src.lower() for x in ["logo", "icon", "avatar", "ads", "placeholder"]):
                continue
            if src.startswith("http") and any(src.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                images.append(src)
                if len(images) > 3: break
                
        # 2. Text Extraction
        content_text = ""
        potential_containers = [
            "article", ".fck_detail", ".detail-content", ".cms-body", ".post-content", 
            ".content-detail", ".article-body", ".content_detail", "#content_detail"
        ]
        
        for selector in potential_containers:
            container = soup.select_one(selector)
            if container:
                for unwanted in container.select("script, style, .sidebar, .ads, .comment"):
                    unwanted.decompose()
                content_text = container.get_text(separator="\n", strip=True)
                if len(content_text) > 200:
                    break
                    
        if len(content_text) < 200:
            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
            content_text = "\n".join(paragraphs)
            
        return {
            "text": content_text if len(content_text) > 100 else None,
            "images": list(dict.fromkeys(images)),
            "final_url": final_url,
            "is_broken": False
        }
                
    except Exception as e:
        logger.debug(f"Error fetching full text from {url}: {e}")
        return None

def fetch_article_full_text(url: str, timeout: int = 15) -> Optional[str]:
    """Synchronous wrapper for fetching full article text."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None 
        res = loop.run_until_complete(fetch_article_full_text_async(url, timeout))
        return res["text"] if res else None
    except Exception:
        return None

# Simple test function
async def test_scraper():
    """Test the HTML scraper."""
    scraper = HTMLScraper()
    print("Testing HTML scraper... (Results in logs if console encoding fails)")
    
    try:
        results = await scraper.scrape_all_available()
        for source, articles in results.items():
            msg = f"\n{source}: {len(articles)} articles found"
            print(msg)
            for article in articles[:3]:
                try:
                    print(f"  - {article['title'][:70]}...")
                except UnicodeEncodeError:
                    print(f"  - {article['title'][:70].encode('ascii', 'replace').decode()}...")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
