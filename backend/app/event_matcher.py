from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Article, Event
from . import broadcast
import re

def _get_tokens(text):
    return set(re.findall(r"\w+", text.lower()))

def upsert_event_for_article(db: Session, article: Article) -> Event:
    # 48-hour Sliding Window logic:
    # Look for an existing event of the same type and province that was updated within the last 48 hours
    window_start = article.published_at - timedelta(hours=48)
    
    # Instead of taking the first one blindly, we verify TITLE SIMILARITY
    candidates = db.query(Event).filter(
        Event.disaster_type == article.disaster_type,
        Event.province == article.province,
        Event.last_updated_at >= window_start,
        Event.last_updated_at <= article.published_at + timedelta(hours=6)
    ).all()

    matched_event = None
    best_score = 0.0
    
    # Simple Jaccard Similarity for Titles
    new_tokens = _get_tokens(article.title)
    
    for cand in candidates:
        cand_tokens = _get_tokens(cand.title)
        intersection = len(new_tokens & cand_tokens)
        union = len(new_tokens | cand_tokens)
        score = intersection / union if union > 0 else 0.0
        
        # Threshold: 0.25 (25% overlap words)
        if score > best_score and score > 0.25:
            best_score = score
            matched_event = cand
            
    # Force match if very specific identifiers exist (Storm names)
    if not matched_event and candidates:
         # Fallback: if both mention specific storm name/number
         pass 

    if matched_event is None:
        # Create a unique key for the new event sequence
        timestamp_slug = article.published_at.strftime("%Y%m%d%H%M")
        unique_key = f"{article.disaster_type}|{article.province}|{timestamp_slug}"
        
        # Guard against key collision
        counter = 0
        while db.query(Event).filter(Event.key == unique_key).first():
            counter += 1
            unique_key = f"{article.disaster_type}|{article.province}|{timestamp_slug}_{counter}"

        ev = Event(
            key=unique_key,
            title=article.title,
            disaster_type=article.disaster_type,
            province=article.province,
            started_at=article.published_at,
            last_updated_at=article.published_at,
            deaths=article.deaths,
            missing=article.missing,
            injured=article.injured,
            damage_billion_vnd=article.damage_billion_vnd,
            confidence=0.25,
            sources_count=1,
        )
        db.add(ev)
        db.flush()
        article.event_id = ev.id
        
        # publish new event to subscribers
        try:
            import asyncio
            asyncio.create_task(broadcast.publish_event({
                "type": "new_event",
                "event_id": ev.id,
                "title": ev.title,
                "disaster_type": ev.disaster_type,
                "province": ev.province,
                "started_at": ev.started_at.isoformat() if ev.started_at else None,
            }))
        except Exception:
            pass
        return ev
    
    # If match found
    ev = matched_event

    # If event exists, we update the window
    ev.last_updated_at = max(ev.last_updated_at, article.published_at)
    ev.started_at = min(ev.started_at, article.published_at)

    # Update impact metrics (take MAX to ensure we have the most severe reporting)
    for field in ["deaths", "missing", "injured"]:
        val = getattr(article, field)
        if val is not None:
            cur = getattr(ev, field)
            setattr(ev, field, max(cur or 0, val))
            
    if article.damage_billion_vnd is not None:
        ev.damage_billion_vnd = max(ev.damage_billion_vnd or 0.0, article.damage_billion_vnd)

    # Aggregating impact_details into ev.details
    if article.impact_details:
        import json
        current_details = dict(ev.details or {})
        new_details = article.impact_details
        
        for key, items in new_details.items():
            if not items: continue
            
            if key not in current_details:
                current_details[key] = items
            else:
                # Merge lists
                existing = current_details[key]
                combined = existing + items
                if not combined: continue
                
                # Dedup strategy
                first_item = combined[0]
                if isinstance(first_item, int):
                    current_details[key] = sorted(list(set(combined)), reverse=True)
                elif isinstance(first_item, dict):
                    seen = set()
                    unique = []
                    for x in combined:
                        u = (x.get("unit") or "").lower().strip()
                        n = x.get("num")
                        sig = f"{n}_{u}"
                        if sig not in seen:
                            seen.add(sig)
                            unique.append(x)
                    current_details[key] = unique
        ev.details = current_details

    # Update source count and smart confidence
    from .sources import SOURCES, VIP_TERMS, SENSITIVE_LOCATIONS
    from . import nlp
    import re
    
    all_articles = ev.articles + [article]
    sources_used = {a.source for a in all_articles}
    ev.sources_count = len(sources_used)
    
    # 1. Check for Strong Signals across all articles in this event
    trusted_map = {s.name: (s.trusted or False) for s in SOURCES}
    has_trusted_source = any(trusted_map.get(a.source, False) for a in all_articles)
    
    # Check for VIP, Sensitive Locations, and Metrics
    has_vip_term = False
    has_sensitive_loc = False
    has_strong_metrics = False
    
    for a in all_articles:
        combined_text = f"{a.title} {a.summary or ''}".lower()
        
        # VIP Check
        if not has_vip_term:
            for vip_pat in VIP_TERMS:
                if re.search(vip_pat, combined_text, re.IGNORECASE):
                    has_vip_term = True; break
        
        # Sensitive Loc Check
        if not has_sensitive_loc:
            for loc in SENSITIVE_LOCATIONS:
                if re.search(rf"(?<!\w){re.escape(loc.lower())}(?!\w)", combined_text):
                    has_sensitive_loc = True; break
        
        # Metrics Check (High rainfall or winds)
        if not has_strong_metrics:
            if a.deaths or a.missing or (a.damage_billion_vnd and a.damage_billion_vnd > 0.5):
                has_strong_metrics = True
    
    # 2. Smart Title Selection: 
    # Use the most descriptive title (often from trusted or longest titles)
    # Prefer title with VIP terms
    best_title = ev.title
    if has_vip_term and not any(re.search(v, best_title.lower()) for v in VIP_TERMS):
        # Current title doesn't have VIP but new article might
        for a in all_articles:
            if any(re.search(v, a.title.lower()) for v in VIP_TERMS):
                best_title = a.title; break
    elif has_trusted_source:
        # If we have trusted sources, prefer their titles (take the longest one for detail)
        trusted_titles = [a.title for a in all_articles if trusted_map.get(a.source, False)]
        if trusted_titles:
            best_title = max(trusted_titles, key=len)
    
    ev.title = best_title

    # 3. Calculate Smart Confidence
    if has_vip_term:
        ev.confidence = 1.0  # Absolute priority (Emergency dispatch)
    elif has_sensitive_loc and has_trusted_source:
        ev.confidence = 0.98 # Strategic infrastructure at risk
    elif has_trusted_source:
        # confirmed by at least one official source
        ev.confidence = 0.95 if ev.sources_count >= 2 else 0.9
    elif has_sensitive_loc:
        ev.confidence = 0.85 if ev.sources_count >= 2 else 0.7
    elif has_strong_metrics:
        ev.confidence = 0.8 if ev.sources_count >= 2 else 0.6
    else:
        # Pure crowd-sourced / general news
        if ev.sources_count == 1:
            ev.confidence = 0.3
        elif ev.sources_count == 2:
            ev.confidence = 0.5
        elif ev.sources_count == 3:
            ev.confidence = 0.75
        else:
            ev.confidence = 0.85

    article.event_id = ev.id
    return ev
