"""
Deduplication strategies for articles.
Helps identify duplicate articles from different sources.
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse, parse_qs
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from .models import Article


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (remove tracking params, fragment, etc)."""
    try:
        parsed = urlparse(url)
        
        # Remove common tracking parameters
        params = parse_qs(parsed.query)
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
            'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'share'
        }
        cleaned_params = {k: v for k, v in params.items() if k.lower() not in tracking_params}
        
        # Reconstruct clean URL
        clean_query = '&'.join(
            f"{k}={'&'.join(v)}" for k, v in sorted(cleaned_params.items())
        ) if cleaned_params else ''
        
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_query:
            normalized += f"?{clean_query}"
        
        return normalized.lower()
    except Exception:
        return url.lower()


def normalize_title(title: str) -> str:
    """Normalize title for similarity comparison."""
    # Remove special chars, convert to lowercase, collapse whitespace
    normalized = re.sub(r'[^\w\s]', '', title).lower()
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def title_similarity(title1: str, title2: str) -> float:
    """Calculate title similarity score (0..1)."""
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Use SequenceMatcher to compare
    matcher = SequenceMatcher(None, norm1, norm2)
    return matcher.ratio()


def find_duplicate_article(
    db: Session,
    domain: str,
    url: str,
    title: str,
    published_at: datetime,
    time_window_hours: int = 24
) -> Optional[Article]:
    """
    Find potential duplicate article from a different source.
    
    Strategy:
    1. Check if exact same URL (normalized) in DB → definite duplicate
    2. Check if same/similar title + same domain + similar publish time → likely duplicate
    3. Check if similar title + different domain + similar publish time → potential duplicate
    
    Returns: Article if found (representing the original), None otherwise
    """
    
    try:
        # Strategy 0: GLOBAL Check for exact URL match (ignoring time window) 
        # This prevents UniqueConstraint violations for re-scraped old articles.
        exact_match = db.query(Article).filter(
            Article.domain == domain,
            Article.url == url
        ).first()
        
        if exact_match:
            return exact_match

        norm_url = normalize_url(url)

        # Candidates in time window
        candidates = db.query(Article).filter(
            Article.published_at >= published_at - timedelta(hours=time_window_hours),
            Article.published_at <= published_at + timedelta(hours=2),
        ).all()

        # Strategy 1: exact normalized URL match against stored url or canonical_url
        for article in candidates:
            try:
                art_norm = normalize_url(article.canonical_url or article.url)
            except Exception:
                art_norm = normalize_url(article.url)
            if art_norm == norm_url:
                return article

        # Strategy 2: Exact title + domain + similar time
        for article in candidates:
            if article.domain == domain and article.title == title:
                return article

        # Strategy 3: Highly similar title across domains (DISABLED to maximize recall)
        # threshold = 0.75
        # for candidate in candidates:
        #     if candidate.domain == domain:
        #         continue
        #     similarity = title_similarity(title, candidate.title)
        #     if similarity >= threshold:
        #         print(f"[INFO] Dedup fuzzy match: '{title}' ~ '{candidate.title}' ({similarity:.2f})")
        #         return candidate
        return None
    except Exception as e:
        print(f"[WARN] dedup check failed: {e}")
        return None


def get_article_hash(title: str, domain: str, url: str | None = None) -> str:
    """Create a hash for article dedup logging. Includes normalized url if provided."""
    parts = [domain, normalize_title(title)]
    if url:
        try:
            parts.append(normalize_url(url))
        except Exception:
            parts.append(url)
    key = "#".join(parts)
    return hashlib.md5(key.encode()).hexdigest()[:12]
