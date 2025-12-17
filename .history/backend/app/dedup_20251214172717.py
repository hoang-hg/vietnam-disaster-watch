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
        # Strategy 1: Normalized URL match (different sources sometimes share links)
        norm_url = normalize_url(url)
        existing_norm_url = db.query(Article).filter(
            Article.published_at >= published_at - timedelta(hours=time_window_hours),
            Article.published_at <= published_at + timedelta(hours=2),  # Allow 2h after
        ).all()
        
        for article in existing_norm_url:
            if normalize_url(article.url) == norm_url:
                return article
        
        # Strategy 2: Exact title + domain + similar time (same source reporting twice)
        exact_match = db.query(Article).filter(
            Article.domain == domain,
            Article.title == title,
            Article.published_at >= published_at - timedelta(hours=time_window_hours),
        ).first()
        
        if exact_match:
            return exact_match
        
        # Strategy 3: Highly similar title + different domain + similar time
        # This catches articles about same event from different sources
        candidates = db.query(Article).filter(
            Article.published_at >= published_at - timedelta(hours=time_window_hours),
            Article.published_at <= published_at + timedelta(hours=2),
        ).all()
        
        threshold = 0.75  # 75% similar title = likely same event
        norm_title = normalize_title(title)
        
        for candidate in candidates:
            # Only cross-domain check (allow same-domain to be different articles)
            if candidate.domain == domain:
                continue
            
            similarity = title_similarity(title, candidate.title)
            
            if similarity >= threshold:
                # Additional check: same disaster type and province = more confident
                return candidate
        
        return None
        
    except Exception as e:
        print(f"[WARN] dedup check failed: {e}")
        return None


def get_article_hash(title: str, domain: str) -> str:
    """Create a hash for article dedup logging."""
    key = f"{domain}#{normalize_title(title)}"
    return hashlib.md5(key.encode()).hexdigest()[:12]
