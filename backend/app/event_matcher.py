from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Article, Event
from . import broadcast
import re

def _get_tokens(text):
    return set(re.findall(r"\w+", text.lower()))

def _get_impact_bucket(article: Article) -> str:
    """Creates a discrete string bucket based on impact severity."""
    d = article.deaths or 0
    m = article.missing or 0
    i = article.injured or 0
    dmg = article.damage_billion_vnd or 0
    
    # Casualties bucket: 0, 1-2, 3-5, 6-10, 11+
    c = d + m
    if c == 0: cb = "zero"
    elif c <= 2: cb = "low"
    elif c <= 5: cb = "mid"
    else: cb = "high"
    
    # Damage bucket: 0, <1B, <10B, 10B+
    if dmg == 0: db = "zero"
    elif dmg < 1: db = "low"
    elif dmg < 10: db = "mid"
    else: db = "high"
    
    return f"{cb}_{db}"

def upsert_event_for_article(db: Session, article: Article) -> Event:
    """
    Groups articles into Events using a Fingerprint Strategy:
    (Hazard, Province, Time_Bucket, Impact_Bucket) + Title Similarity.
    """
    # 1. Broad Candidate Search (24h window for new events)
    window_start = article.published_at - timedelta(hours=24)
    window_end = article.published_at + timedelta(hours=12)
    
    impact_bucket = _get_impact_bucket(article)
    
    candidates = db.query(Event).filter(
        Event.disaster_type == article.disaster_type,
        Event.province == article.province,
        Event.last_updated_at >= window_start,
        Event.last_updated_at <= window_end
    ).all()

    matched_event = None
    best_score = 0.0
    new_tokens = _get_tokens(article.title)
    
    for cand in candidates:
        # Strict Match if they share the same Impact Bucket and moderate Title match
        # OR High Title similarity (80%+) even if buckets slightly differ (as numbers evolve)
        cand_tokens = _get_tokens(cand.title)
        intersection = len(new_tokens & cand_tokens)
        union = len(new_tokens | cand_tokens)
        title_sim = intersection / union if union > 0 else 0.0
        
        # Heuristic: Bucket match gives a strong boost
        cand_impact_bucket = cand.details.get("impact_bucket") if cand.details else None
        bucket_match = (impact_bucket == cand_impact_bucket)
        
        score = title_sim
        if bucket_match: score += 0.3 # Strong priority for similar severity
        
        if score > best_score and score > 0.6:
            best_score = score
            matched_event = cand

    if matched_event is None:
        # Create a unique key for the new event sequence
        timestamp_slug = article.published_at.strftime("%Y%m%d%H%M")
        unique_key = f"{article.disaster_type}|{article.province}|{timestamp_slug}"
        
        # Guard against key collision
        counter = 0
        while db.query(Event).filter(Event.key == unique_key).first():
            counter += 1
            unique_key = f"{article.disaster_type}|{article.province}|{timestamp_slug}_{counter}"

        # Get coordinates for the province
        from .nlp import PROVINCE_COORDINATES
        coords = PROVINCE_COORDINATES.get(article.province, [None, None])

        ev = Event(
            key=unique_key,
            title=article.title,
            disaster_type=article.disaster_type,
            province=article.province,
            stage=article.stage,
            started_at=article.published_at,
            last_updated_at=article.published_at,
            deaths=article.deaths,
            missing=article.missing,
            injured=article.injured,
            damage_billion_vnd=article.damage_billion_vnd,
            confidence=0.5 if article.deaths or article.needs_verification else 0.3, # Initial confidence
            sources_count=1,
            lat=coords[0],
            lon=coords[1],
            needs_verification=article.needs_verification,
            commune=article.commune,
            village=article.village,
            route=article.route,
            cause=article.cause,
            characteristics=article.characteristics,
            details={"impact_bucket": impact_bucket}
        )
        db.add(ev)
        db.flush()
        article.event_id = ev.id
        
        # publish new event to subscribers
        try:
            import asyncio
            data = {
                "type": "new_event",
                "event_id": ev.id,
                "title": ev.title,
                "disaster_type": ev.disaster_type,
                "province": ev.province,
                "started_at": ev.started_at.isoformat() if ev.started_at else None,
            }
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broadcast.publish_event(data))
            except RuntimeError:
                # No running loop (likely running from a script or background worker outside FastAPI loop)
                # We still append to buffer as publish_event does internally (but publish_event is async)
                msg = broadcast._make_message(data)
                broadcast._append_to_buffer(msg)
        except Exception:
            pass
        return ev
    
    # If match found, update event metrics
    ev = matched_event

    # UPDATE LEADER: If this article is from a trusted source or is more detailed, update title
    # We compare using a length-weighted trusted score
    from .sources import SOURCES
    trusted_map = {s.name: (s.trusted or False) for s in SOURCES}
    
    current_lead_is_trusted = trusted_map.get(ev.articles[0].source, False) if ev.articles else False
    new_is_trusted = trusted_map.get(article.source, False)
    
    # Swap criteria: (Trusted wins over non-trusted) OR (Longer titles if both equal trust)
    if (new_is_trusted and not current_lead_is_trusted) or \
       (new_is_trusted == current_lead_is_trusted and len(article.title) > len(ev.title) + 5):
        ev.title = article.title
        # Keep old details but update bucket if this is a more severe report
        if ev.details is None:
            ev.details = {}
        ev.details["impact_bucket"] = impact_bucket

    # Update Stage (Recovery > Incident > Forecast)
    stage_priority = {"FORECAST": 1, "INCIDENT": 2, "RECOVERY": 3}
    if stage_priority.get(article.stage, 0) > stage_priority.get(ev.stage, 0):
        ev.stage = article.stage

    ev.last_updated_at = max(ev.last_updated_at, article.published_at)
    ev.started_at = min(ev.started_at, article.published_at)

    # Update global event impact metrics (Cumulative logic)
    # Note: For deaths/missing, if sources report DIFFERENT numbers for SAME event, 
    # we take MAX (following government directive to use highest confirmed count)
    for field in ["deaths", "missing", "injured"]:
        val = getattr(article, field)
        if val is not None:
            setattr(ev, field, max(getattr(ev, field) or 0, val))
            
    if article.damage_billion_vnd:
        ev.damage_billion_vnd = max(ev.damage_billion_vnd or 0.0, article.damage_billion_vnd)

    if article.needs_verification:
        ev.needs_verification = 1

    # Update location details in Event if article has more specific info
    if article.commune and not ev.commune: ev.commune = article.commune
    if article.village and not ev.village: ev.village = article.village
    if article.route and not ev.route: ev.route = article.route
    if article.cause and not ev.cause: ev.cause = article.cause
    if article.characteristics and not ev.characteristics: ev.characteristics = article.characteristics

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
    from .sources import SOURCES, VIP_TERMS_RE, SENSITIVE_LOCATIONS_RE
    from . import nlp
    
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
            for vip_re in VIP_TERMS_RE:
                if vip_re.search(combined_text):
                    has_vip_term = True; break
        
        # Sensitive Loc Check
        if not has_sensitive_loc:
            for loc_re in SENSITIVE_LOCATIONS_RE:
                if loc_re.search(combined_text):
                    has_sensitive_loc = True; break
        
        # Metrics Check (High rainfall or winds)
        if not has_strong_metrics:
            if a.deaths or a.missing or (a.damage_billion_vnd and a.damage_billion_vnd > 0.5):
                has_strong_metrics = True
    
    # 2. Smart Title Selection: 
    # Use the most descriptive title (often from trusted or longest titles)
    # Prefer title with VIP terms
    best_title = ev.title
    if has_vip_term and not any(pat.search(best_title.lower()) for pat in VIP_TERMS_RE):
        # Current title doesn't have VIP but new article might
        for a in all_articles:
            if any(pat.search(a.title.lower()) for pat in VIP_TERMS_RE):
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
    
    # Real-time Broadcast: Notify subscribers of event updates
    try:
        import asyncio
        asyncio.create_task(broadcast.publish_event({
            "type": "event_updated",
            "event_id": ev.id,
            "title": ev.title,
            "disaster_type": ev.disaster_type,
            "province": ev.province,
            "deaths": ev.deaths,
            "missing": ev.missing,
            "injured": ev.injured,
            "damage": ev.damage_billion_vnd,
            "confidence": ev.confidence,
            "sources_count": ev.sources_count,
            "last_updated": ev.last_updated_at.isoformat() if ev.last_updated_at else None
        }))
    except Exception:
        pass

    return ev
