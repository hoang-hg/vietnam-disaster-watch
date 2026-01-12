from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Article, Event
from . import broadcast, nlp
from .cache import cache
import re

from .sources import SOURCES
import logging
import asyncio

logger = logging.getLogger(__name__)

# Clusters of related disaster types to allow cross-matching (e.g. Storm causes Flood)
DISASTER_CLUSTERS = {
    "storm": ["storm", "extreme_weather", "storm_surge", "flood"],
    "flood": ["flood", "flash_flood", "landslide", "storm", "extreme_weather"],
    "flash_flood": ["flash_flood", "landslide", "flood"],
    "landslide": ["landslide", "flash_flood", "subsidence", "erosion"],
    "drought": ["drought", "salinity", "heatwave"],
    "salinity": ["salinity", "drought"],
    "earthquake": ["earthquake", "tsunami"],
    "tsunami": ["tsunami", "earthquake"],
    "erosion": ["erosion", "landslide", "subsidence"],
    "heatwave": ["heatwave", "drought"],
    "cold_surge": ["cold_surge", "extreme_weather"],
    "wildfire": ["wildfire", "drought", "heatwave"],
    "extreme_weather": ["extreme_weather", "storm", "flood", "cold_surge"],
}

# [OPTIMIZATION] Cache trusted map
TRUSTED_MAP = {s.name: (s.trusted or False) for s in SOURCES}

# Vietnamese stop words to improve similarity accuracy
STOPWORDS = {
    "về", "của", "tại", "và", "những", "các", "là", "bị", "cho", "đến", "trong", "do",
    "đã", "đang", "sẽ", "có", "một", "với", "này", "qua", "trên", "dưới", "tờ", "báo",
    "việc", "vừa", "mới", "vẫn", "được", "rất", "hay", "như", "nhưng", "nếu", "thì",
    "người", "khiến", "gây", "nhiều", "nơi", "bộ", "theo", "tin", "từ", "làm", "sự",
    "vào", "ra"
}

# Pre-compiled regex for tokenization
# Pre-compiled regex for tokenization - Modified to keep Vietnamese characters
TOKEN_CLEAN_RE = re.compile(r"[^\w\s\u00C0-\u1EF9]", re.UNICODE)

def _get_tokens(text):
    if not text: return set(), set()
    # Normalize: lowercase, remove special characters
    text = TOKEN_CLEAN_RE.sub(" ", text.lower())
    words = [t for t in text.split() if t not in STOPWORDS and not t.isdigit() and len(t) > 1]
    
    # 1-grams
    unigrams = set(words)
    
    # 2-grams (bigrams) for semantic context (e.g., "nước dâng", "mưa lớn")
    bigrams = set()
    if len(words) >= 2:
        for i in range(len(words) - 1):
            bigrams.add(f"{words[i]} {words[i+1]}")
            
    return unigrams, bigrams

def _calculate_similarity(tokens1, tokens2):
    """Calculates a hybrid Jaccard similarity for unigrams and bigrams."""
    u1, b1 = tokens1
    u2, b2 = tokens2
    
    # Unigram similarity
    u_inter = len(u1 & u2)
    u_union = len(u1 | u2)
    u_sim = u_inter / u_union if u_union > 0 else 0.0
    
    # Bigram similarity (higher weight for semantic matching)
    b_inter = len(b1 & b2)
    b_union = len(b1 | b2)
    b_sim = b_inter / b_union if b_union > 0 else 0.0
    
    # Weighted average: Balanced for robustness
    if b_union > 0:
        return (u_sim * 0.5) + (b_sim * 0.5)
    return u_sim

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

def upsert_event_for_article(db: Session, article: Article) -> tuple[Event, bool]:
    """Groups articles into Events using a Fingerprint Strategy."""
    # 1. Match/Find Candidate
    matched_event, best_score = _find_best_match(db, article)

    if matched_event is None:
        # 2. Create New Event if no match
        return _create_new_event(db, article), True
    
    # 3. Update Existing Event
    ev = matched_event
    _update_event_from_article(db, ev, article)
    
    # 4. Finalize: Consensus checks
    _finalize_event_upsert(db, ev, article)
    return ev, False

def _find_best_match(db: Session, article: Article) -> tuple[Event | None, float]:
    """Search for the most similar existing event in the same location/time window."""
    window_start = article.published_at - timedelta(hours=24)
    window_end = article.published_at + timedelta(hours=12)
    
    is_meta_type = article.disaster_type in ("recovery", "warning_forecast")
    
    query = db.query(Event).filter(
        Event.province == article.province,
        Event.last_updated_at >= window_start,
        Event.last_updated_at <= window_end
    )
    
    if not is_meta_type:
        cluster = DISASTER_CLUSTERS.get(article.disaster_type, [article.disaster_type])
        query = query.filter(Event.disaster_type.in_(cluster))
        
    candidates = query.all()
    matched_event = None
    best_score = 0.0
    new_tokens = _get_tokens(article.title)
    
    for cand in candidates:
        cand_tokens = _get_tokens(cand.title)
        title_sim = _calculate_similarity(new_tokens, cand_tokens)
        
        # Lower threshold to 0.3 to catch different phrasings of same event
        if title_sim < 0.30: continue

        score = title_sim
        # LOCATION BOOST: Strong evidence for merging
        if article.commune and cand.commune and article.commune.lower() == cand.commune.lower(): score += 0.3
        if article.village and cand.village and article.village.lower() == cand.village.lower(): score += 0.4
        if article.landmark and cand.landmark and article.landmark.lower() == cand.landmark.lower(): score += 0.4
        if article.route and cand.route and article.route.lower() == cand.route.lower(): score += 0.3
            
        if score > 0.7 and score > best_score:
            best_score = score
            matched_event = cand
            
    return matched_event, best_score


def _create_new_event(db: Session, article: Article) -> Event:
    """Initialize a new event from an article."""
    timestamp_slug = article.published_at.strftime("%Y%m%d%H%M")
    unique_key = f"{article.disaster_type}|{article.province}|{timestamp_slug}"
    
    # Guard against key collision (rare but possible in high-volume bursts)
    counter = 0
    while db.query(Event.id).filter(Event.key == unique_key).first():
        counter += 1
        unique_key = f"{article.disaster_type}|{article.province}|{timestamp_slug}_{counter}"

    from .nlp import PROVINCE_COORDINATES
    coords = PROVINCE_COORDINATES.get(article.province, [None, None])

    # [LOGIC CHANGE] Admin Approved = Verified & High Confidence
    is_approved = article.status == "approved"

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
        confidence=1.0 if is_approved else (0.5 if article.deaths or article.needs_verification else 0.3),
        sources_count=1,
        lat=coords[0], lon=coords[1],
        needs_verification=False if is_approved else article.needs_verification,
        commune=article.commune, village=article.village,
        route=article.route, landmark=article.landmark,
        location_description=article.location_description,
        cause=article.cause, characteristics=article.characteristics,
        details={"impact_bucket": _get_impact_bucket(article)}
    )
    db.add(ev)
    db.flush()
    article.event_id = ev.id

    # 1. Broadcast and Notify handled by caller via emit_event_notifications
    _invalidate_event_caches(ev.id)
    return ev



def _update_event_from_article(db: Session, ev: Event, article: Article):
    """Update event fields based on new article signals."""
    # Update Title logic: Trusted or more detailed wins
    try:
        current_leader_trusted = TRUSTED_MAP.get(db.query(Article.source).filter(Article.event_id == ev.id).order_by(Article.id).limit(1).scalar(), False)
    except Exception:
        current_leader_trusted = False
    
    new_is_trusted = TRUSTED_MAP.get(article.source, False)
    
    if (new_is_trusted and not current_leader_trusted) or \
       (new_is_trusted == current_leader_trusted and len(article.title) > len(ev.title) + 5):
        ev.title = article.title
        if ev.details is None: ev.details = {}
        ev.details["impact_bucket"] = _get_impact_bucket(article)

    # Type & Stage Upgrades
    if article.disaster_type != ev.disaster_type:
        prio = nlp.DISASTER_PRIORITY_MAP
        if prio.get(article.disaster_type, 99) < prio.get(ev.disaster_type, 99):
            ev.disaster_type = article.disaster_type

    stage_priority = {"FORECAST": 1, "INCIDENT": 2, "RECOVERY": 3}
    if stage_priority.get(article.stage, 0) > stage_priority.get(ev.stage, 0):
        ev.stage = article.stage

    # Location & Metrics
    for attr in ["commune", "village", "route", "landmark"]:
        if not getattr(ev, attr) and getattr(article, attr):
            setattr(ev, attr, getattr(article, attr))
    
    if article.location_description and len(article.location_description) > len(ev.location_description or ""):
        ev.location_description = article.location_description

    ev.last_updated_at = max(ev.last_updated_at, article.published_at)
    ev.started_at = min(ev.started_at, article.published_at)

    for field in ["deaths", "missing", "injured"]:
        val = getattr(article, field)
        if val is not None: setattr(ev, field, max(getattr(ev, field) or 0, val))
            
    if article.damage_billion_vnd:
        ev.damage_billion_vnd = max(ev.damage_billion_vnd or 0.0, article.damage_billion_vnd)

    if article.needs_verification: ev.needs_verification = True
    
    # Merge impact_details
    if article.impact_details:
        _merge_impact_details(ev, article.impact_details)

def _merge_impact_details(ev: Event, new_details: dict):
    if not ev.details: ev.details = {}
    current = dict(ev.details)
    for key, items in new_details.items():
        if not items: continue
        if key not in current: 
            current[key] = items
        else:
            combined = current[key] + items
            # Dedup strategy for dicts (impact objects)
            seen, unique = set(), []
            for x in combined:
                if isinstance(x, dict):
                    num = x.get('num')
                    if num is not None:
                        sig = f"{num}_{x.get('unit', '').lower().strip()}"
                    else:
                        # Fallback for metrics or generic dicts: Deterministic JSON string
                        # Sort keys to ensure {"a":1, "b":2} == {"b":2, "a":1}
                        import json
                        sig = json.dumps(x, sort_keys=True)
                        
                    if sig not in seen:
                        seen.add(sig); unique.append(x)
                else: unique.append(x)
            current[key] = unique if (combined and isinstance(combined[0], dict)) else sorted(list(set(combined)), reverse=True)
    ev.details = current

def _finalize_event_upsert(db: Session, ev: Event, article: Article):
    """Final consensus check, confidence scoring, notifications and broadcast."""
    from sqlalchemy import or_
    from .sources import VIP_TERMS_RE
    
    # Batch fetch flat article data in 1 query
    article_data = db.query(Article.domain, Article.source, Article.status, Article.title)\
        .filter(Article.event_id == ev.id).all()
    
    all_domains = {r.domain for r in article_data if r.domain}
    all_sources = {r.source for r in article_data if r.source}
    if article.domain: all_domains.add(article.domain)
    if article.source: all_sources.add(article.source)
    
    ev.sources_count = len(all_sources)

    # 1. Consensus Promotion
    if len(all_domains) >= 3:
        db.query(Article).filter(Article.event_id == ev.id, Article.status == "pending").update({"status": "approved"})

    # 2. Strong Signal Checks
    has_trusted = any(TRUSTED_MAP.get(s, False) for s in all_sources)
    has_strong_metrics = (ev.deaths or 0) > 0 or (ev.missing or 0) > 0 or (ev.damage_billion_vnd or 0) > 0.5
    
    # Use pre-compiled mega-regex for titles
    has_vip = False
    if VIP_TERMS_RE and VIP_TERMS_RE.search(article.title):
        has_vip = True
    
    # 3. Smart Confidence Matrix
    # [LOGIC CHANGE] Admin Approved overrides all algorithm scores
    if article.status == "approved":
        ev.confidence = 1.0
        ev.needs_verification = False
    elif has_vip: ev.confidence = 1.0
    elif has_trusted: ev.confidence = 0.95 if ev.sources_count >= 2 else 0.9
    elif has_strong_metrics: ev.confidence = 0.8 if ev.sources_count >= 2 else 0.6
    else:
        # Logistic curve approximation
        ev.confidence = min(0.1 + (ev.sources_count * 0.25), 0.85)


    article.event_id = ev.id
    
    # [OPTIMIZATION]
    # Removed direct side-effects (Notifications/Broadcast) from here to avoid Race Conditions.
    # The caller (crawler/api) must call `emit_event_notifications` AFTER committing the transaction.
    _invalidate_event_caches(ev.id)

def emit_event_notifications(db: Session, event_id: int, is_new: bool = False):
    """
    Triggers Broadcasts and Background Notifications.
    MUST be called AFTER db.commit() to ensure data visibility.
    """
    try:
        ev = db.query(Event).get(event_id)
        if not ev: return

        # 1. Broadcast (Fast, in-memory)
        _broadcast_event(ev, is_new=is_new)
        

        # 2. Notifications (Slow, DB-heavy) -> Offload to thread
        import threading
        t = threading.Thread(target=_background_notify_wrapper, args=(ev.id,))
        t.daemon = True 
        t.start()
        
        # 3. Notify followers of this specific event update (if not new)
        if not is_new:
             # notify_followers_of_article(db, ev, None) 
             # SKIP: requires 'article' context which is not available here. 
             # We rely on 'events_updated' broadcast for general UI updates.
             pass

    except Exception as e:
        logger.error(f"Failed to emit notifications for event {event_id}: {e}")

def _background_notify_wrapper(evt_id):
    # Create a dedicated session for the background thread
    from .database import SessionLocal
    bg_db = SessionLocal()
    try:
        # Re-fetch event to ensure it's attached to this session
        bg_ev = bg_db.query(Event).get(evt_id)
        if bg_ev:
            from .notifications import notify_users_of_event
            # Triggers province-based notifications for new events
            notify_users_of_event(bg_db, bg_ev) 
            bg_db.commit() # [FIX] Ensure notifications are persisted
            
            # Use this background thread to also notify followers if needed
            # But notify_followers_of_article requires the 'Article' object which triggered this.
            # Since we decoupled, we might lose that context unless passed.
            # However, for massive crawls, individual article notifications might be spammy.
            # We focus on "New Event" notifications primarily.
    except Exception as e:
        bg_db.rollback() # Ensure rollback on error

        logger.error(f"Background notification failed for event {evt_id}: {e}")
    finally:
        bg_db.close()

def _invalidate_event_caches(event_id: int):
    """Invalidate all caches related to events."""
    try:
        # Invalidate specific event details
        cache.delete(f"ev_detail_v3_{event_id}_True")
        cache.delete(f"ev_detail_v3_{event_id}_False")
        cache.delete_match(f"ev_detail_v3_{event_id}*")
        
        # Invalidate lists and stats
        cache.delete_match("ev_v2_*")
        cache.delete_match("stats_*")
        cache.delete_match("articles_latest_*")
        cache.delete_match("map_*")
    except Exception as e:
        logger.error(f"Cache invalidation failed for event {event_id}: {e}")


def _broadcast_event(ev: Event, is_new: bool = False):
    """Universal broadcast to real-time channels."""
    try:
        data = {
            "type": "new_event" if is_new else "event_updated",
            "event_id": ev.id,
            "title": ev.title,
            "disaster_type": ev.disaster_type,
            "province": ev.province,
            "deaths": ev.deaths,
            "missing": ev.missing,
            "damage": ev.damage_billion_vnd,
            "confidence": ev.confidence,
            "sources_count": ev.sources_count,
            "last_updated": ev.last_updated_at.isoformat() if ev.last_updated_at else None
        }
        broadcast.publish_event_sync(data)
        from .ws import manager
        manager.broadcast_sync({"type": "EVENT_UPSERT", "data": data})
    except Exception as e:
        logger.error(f"Failed to broadcast event {ev.id}: {e}")

