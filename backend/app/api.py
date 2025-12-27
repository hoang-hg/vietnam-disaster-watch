from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from sqlalchemy.sql import text
from .database import get_db, engine
from . import models
from .models import Article, Event, Blacklist, CrawlerStatus, AiFeedback
from .schemas import ArticleOut, EventOut, EventDetailOut, EventUpdate
from datetime import datetime, timedelta
from fastapi import Response, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from .event_matcher import upsert_event_for_article
import asyncio
from pathlib import Path
import json
from .nlp import RECOVERY_KEYWORDS, PROVINCES
from .sources import DISASTER_KEYWORDS
from .risk_lookup import canon
from . import broadcast, auth
from .cache import cache
import time
import io
from typing import Optional

# stats_cache is now replaced by centralized 'cache' from .cache

# Unified filtering rules for Dashboard/Stats
def filter_disaster_events(events):
    filtered = []
    for ev in events:
        # Exclusion: Skip unknown/other or events with NO articles/sources
        if ev.disaster_type in ["unknown", "other", None] or (ev.sources_count or 0) == 0:
            continue
            
        # Decision 18 Logic: Skip purely administrative news if no impact and not a major hazard
        is_impacting = (ev.deaths or 0) > 0 or (ev.missing or 0) > 0 or (ev.injured or 0) > 0 or (ev.damage_billion_vnd or 0) > 0
        major_hazards = [
            "storm", "flood", "flash_flood", "landslide", "subsidence", 
            "drought", "salinity", "extreme_weather", "heatwave", "cold_surge", 
            "earthquake", "tsunami", "storm_surge", "wildfire",
            "warning_forecast", "recovery"
        ]
        
        if not is_impacting and ev.disaster_type not in major_hazards:
             d = ev.details or {}
             if not (d.get("homes") or d.get("agriculture") or d.get("infrastructure") or d.get("marine")):
                # Likely administrative/routine news
                continue
        filtered.append(ev)
    return filtered

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/articles/latest", response_model=list[ArticleOut])
def latest_articles(
    limit: int = Query(50, ge=1, le=200),
    type: str | None = Query(None),
    province: str | None = Query(None),
    exclude_unknown: bool = Query(False),
    db: Session = Depends(get_db),
):
    cache_key = f"articles_latest_{limit}_{type}_{province}_{exclude_unknown}"
    cached = cache.get(cache_key)
    if cached: return cached

    q = db.query(Article).filter(Article.status == "approved").order_by(desc(Article.published_at))
    if type:
        q = q.filter(Article.disaster_type == type)
    if province:
        q = q.filter(Article.province == province)
    if exclude_unknown:
        q = q.filter(Article.disaster_type != 'unknown')
    
    res = q.limit(limit).all()
    cache.set(cache_key, res, ttl=120)
    return res

# Optimized filtering logic: move simple filters to DB to reduce payload
def get_base_event_query(db: Session):
    # Defer heavy fields for list views to save memory and I/O
    from sqlalchemy.orm import defer
    return db.query(Event).options(
        defer(Event.cause),
        defer(Event.characteristics),
        defer(Event.details)
    )

@router.get("/events")
def events(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    hours: int | None = Query(None, ge=1, le=720),
    type: str | None = Query(None),
    province: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    q: str | None = Query(None),
    date: str | None = Query(None),
    wrapper: bool = Query(False),
    db: Session = Depends(get_db),
    sort: str = Query("impact"),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    is_admin = current_user and current_user.role == "admin"
    
    # Cache optimization - include is_admin, offset, and wrapper in key
    cache_key = f"ev_v2_{limit}_{offset}_{hours}_{type}_{province}_{start_date}_{end_date}_{q}_{date}_{sort}_{is_admin}_{wrapper}"
    cached = cache.get(cache_key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        # Since we use public cache, ensure we don't leak admin-only fields if that becomes a concern,
        # but currently logic is consistent.
        response.headers["Cache-Control"] = "public, max-age=60"
        return cached

    query = db.query(Event)

    # 1. Base Security / Visibility Filter
    if not is_admin:
        # Public users:
        # - Show if confidence >= 0.8
        # - OR if needs_verification=0 AND sources_count >= 2
        # - Hide filtered keywords (handled by nlp mostly, but ensuring DB cleanliness)
        from sqlalchemy import or_
        query = query.filter(or_(
            Event.confidence >= 0.8,
            (Event.needs_verification == 0) & (Event.sources_count >= 2)
        ))

    # 2. Database-level filters (The "Easy" part of filter_disaster_events)
    # We always exclude unknown/other at the DB level for performance
    query = query.filter(Event.disaster_type.notin_(["unknown", "other"]))
    # Optimization: Filter empty sources in DB
    query = query.filter(Event.sources_count > 0)

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            query = query.filter(Event.started_at >= start, Event.started_at < end)
        except ValueError: pass
    elif hours:
        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(Event.last_updated_at >= since)

    if type: query = query.filter(Event.disaster_type == type)
    if province: query = query.filter(Event.province == province)
    if q: query = query.filter(Event.title.ilike(f"%{q}%"))
    
    if start_date:
        try: query = query.filter(Event.started_at >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError: pass
    if end_date:
        try: query = query.filter(Event.started_at < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
        except ValueError: pass

    # Calculate total if wrapper is requested
    total_count = 0
    if wrapper:
        total_count = query.count()

    # 4. Apply Sorting (MUST be done before Limit/Offset for correct pagination)
    if sort == "latest":
        query = query.order_by(desc(Event.started_at), desc(Event.last_updated_at))
    else:
        # Default or Impact sort
        # Note: Complex Python sort (deaths+missing+injured) is harder in pure SQL, 
        # but for pagination we need stable SQL sort. 
        # We approximate 'impact' as deaths then damage then sources.
        query = query.order_by(
            desc(Event.deaths), 
            desc(Event.damage_billion_vnd),
            desc(Event.sources_count),
            desc(Event.started_at)
        )

    # 3. Fetch candidates (Use limit and offset directly)
    filtered = query.limit(limit).offset(offset).all()
    
    # Legacy Python Sort (Removed as it breaks pagination)
    # if sort == "latest": ...
    
    if not filtered:
        return []

    # 5. [OPTIMIZATION] Fix N+1: Batch Fetch Article Counts
    event_ids = [e.id for e in filtered]
    
    # Count approved articles per event in one query
    count_q = db.query(Article.event_id, func.count(Article.id)).filter(
        Article.event_id.in_(event_ids),
        Article.status == "approved"
    )
    if hours:
        h_start = datetime.utcnow() - timedelta(hours=hours)
        count_q = count_q.filter(Article.published_at >= h_start)
    
    counts_map = {row[0]: row[1] for row in count_q.group_by(Article.event_id).all()}

    # 6. [OPTIMIZATION] Fix N+1: Batch Fetch Images & Sources
    # We use a subquery/distinct to get the latest article for each event in the batch
    # Prioritizing 'approved' status then latest publication date
    from sqlalchemy import and_
    subq = db.query(
        Article.event_id,
        Article.image_url,
        Article.source,
        Article.url,
        func.row_number().over(
            partition_by=Article.event_id,
            order_by=[desc(Article.status == "approved"), desc(Article.published_at)]
        ).label("rn")
    ).filter(
        Article.event_id.in_(event_ids),
        Article.status.in_(["approved", "pending"])
    ).subquery()
    
    leads = db.query(subq).filter(subq.c.rn == 1).all()
    leads_map = {row.event_id: (row.image_url, row.source, row.url) for row in leads}

    # 7. Final response assembly
    events_out = []
    for ev in filtered:
        # We manually map to avoid multiple DB hits from ORM attributes
        ev_data = EventOut.model_validate(ev)
        ev_id = ev.id
        
        ev_data.articles_count = counts_map.get(ev_id, 0)
        
        img, src, url = leads_map.get(ev_id, (None, None, None))
        ev_data.image_url = img
        ev_data.source = src
        ev_data.source_url = url
        
        # Inject Fallback Image
        if not ev_data.image_url:
            chosen_img = DEFAULT_IMAGES.get(ev.disaster_type, DEFAULT_IMAGES["unknown"])
            if ev.disaster_type == "extreme_weather" and "mưa đá" in (ev.title or "").lower():
                chosen_img = SUB_IMAGES["hail"]
            ev_data.image_url = chosen_img
        
        # [NEW] Check logic: if it has manual location_description, prefer it over province text?
        # Actually EventOut already includes location_description, frontend handles display.

        events_out.append(ev_data)

    final_result = [e.model_dump() for e in events_out]
    if wrapper:
        result = {"items": final_result, "total": total_count}
        cache.set(cache_key, result, ttl=300)
        response.headers["Cache-Control"] = "public, max-age=300"
        return result
    else:
        cache.set(cache_key, final_result, ttl=300)
        response.headers["Cache-Control"] = "public, max-age=300"
        return events_out

# Lightweight SVGs (stable CDN, pinned version)
DEFAULT_IMAGES = {
    "storm": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/cloud-storm.svg",
    "flood": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/droplet.svg",
    "flash_flood": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/droplet.svg",
    "landslide": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/triangle.svg",
    "subsidence": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/arrow-down-circle.svg",
    "drought": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/sun-off.svg",
    "salinity": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/ripple.svg",
    "extreme_weather": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/cloud-lightning.svg",
    "heatwave": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/sun.svg",
    "cold_surge": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/snowflake.svg",
    "earthquake": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/activity.svg",
    "tsunami": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/droplet.svg",
    "storm_surge": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/ripple.svg",
    "wildfire": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/flame.svg",
    "warning_forecast": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/alert-circle.svg",
    "recovery": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/tool.svg",
    "unknown": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/urgent.svg",
}

SUB_IMAGES = {
    # “landslide”: không có icon chuyên “sạt lở” trong bộ v1.13.0, dùng biểu tượng “sườn dốc” (triangle) làm proxy.
    "landslide": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/triangle.svg",

    # “tsunami/storm surge”: bộ v1.13.0 không có “wave” rõ ràng, dùng droplet (nước dâng) làm proxy.
    "tsunami": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/droplet.svg",

    # “hail”: dùng snowflake làm proxy (mưa đá/hạt băng).
    "hail": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/snowflake.svg",
}

@router.get("/events/{event_id}", response_model=EventDetailOut)
def event_detail(event_id: int, response: Response, db: Session = Depends(get_db)):
    # 1. Try Cache
    cache_key = f"ev_detail_{event_id}"
    cached = cache.get(cache_key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=60" # 1 min cache for specific events
        return cached

    # 2. Optimized Fetch (Fixes N+1 and lazy loading lag)
    ev = db.query(Event).options(
        joinedload(Event.articles)
    ).filter(Event.id == event_id).first()
    
    if not ev:
        raise HTTPException(status_code=404, detail="Sự kiện không tồn tại.")
        
    # 3. Filter and Sort Articles
    # Only show relevant articles (approved/pending)
    articles = [a for a in ev.articles if a.status in ("approved", "pending")]
    articles.sort(key=lambda x: x.published_at, reverse=True)
    
    # We create a dictionary to avoid ORM lazy load issues after sorting
    ev_data = EventDetailOut.model_validate(ev)
    ev_data.articles = [ArticleOut.model_validate(a) for a in articles]
    
    # Update count to match visible list
    ev_data.sources_count = len(set(a.source for a in articles))
    
    # 4. Save to Cache
    result = ev_data.model_dump()
    cache.set(cache_key, result, ttl=300)
    
    response.headers["Cache-Control"] = "public, max-age=60"
    return result

@router.put("/events/{event_id}", response_model=EventOut)
def update_event(
    event_id: int, 
    payload: EventUpdate, 
    db: Session = Depends(get_db)
):
    """Update event details (admin only logic in production)."""
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    
    # Audit logging for manual correction
    try:
        logs_dir = Path(__file__).resolve().parents[1] / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        audit_file = logs_dir / 'audit_log.jsonl'
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_id': event_id,
            'changes': update_data,
            'action': 'manual_correction'
        }
        with audit_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except: pass

    # Apply changes
    for field, value in update_data.items():
        setattr(ev, field, value)
    
    ev.last_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ev)
    return ev

@router.delete("/events/{event_id}", status_code=204)
def delete_event(
    event_id: int, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    """
    Delete an event (admin only).
    Also updates associated articles to 'rejected' status so they don't reappear.
    """
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Add all associated article hashes to Blacklist before unlinking
    articles = db.query(Article).filter(Article.event_id == event_id).all()
    for art in articles:
        if art.news_hash:
            existing_bl = db.query(Blacklist).filter(Blacklist.news_hash == art.news_hash).first()
            if not existing_bl:
                db.add(Blacklist(
                    news_hash=art.news_hash,
                    title=art.title,
                    reason=f"Admin deleted parent event: {ev.title}"
                ))

    # Mark all associated articles as Rejected/Hidden
    db.query(Article).filter(Article.event_id == event_id).update(
        {"status": "rejected", "event_id": None}, 
        synchronize_session=False
    )
    
    # Delete the event
    db.delete(ev)
    db.commit()
    
    # Invalidate cache
    cache.delete(f"ev_detail_{event_id}")
    cache.delete_match("stats_*")
    cache.delete_match("articles_latest_*")
    
    return

@router.delete("/articles/{article_id}", status_code=204)
def delete_article(
    article_id: int, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    """
    Delete/Reject an article (admin only).
    """
    art = db.query(Article).filter(Article.id == article_id).first()
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
        
    # Save event_id to check for orphans
    old_event_id = art.event_id
    
    # Mark as Rejected and Unlink
    art.status = "rejected"
    art.event_id = None
    
    # Also add to persistent Blacklist table
    if art.news_hash:
        existing_bl = db.query(Blacklist).filter(Blacklist.news_hash == art.news_hash).first()
        if not existing_bl:
            db.add(Blacklist(
                news_hash=art.news_hash,
                title=art.title,
                reason="Admin explicitly deleted article"
            ))
            
    db.commit()

    # Cleanup: If the event has no more approved/pending articles, delete it
    if old_event_id:
        remaining = db.query(Article).filter(Article.event_id == old_event_id).count()
        if remaining == 0:
            db.query(Event).filter(Event.id == old_event_id).delete()
            db.commit()
            # Clear cache as an event disappeared
            cache.delete_match(f"ev_detail_{old_event_id}*")
            cache.delete_match("stats_*")
            cache.delete_match("articles_latest_*")
    
    # Always clear the detail of the article's parent event even if not deleted
    if old_event_id:
        cache.delete(f"ev_detail_{old_event_id}")

    return



@router.get("/stats/summary")
def stats_summary(
    hours: int = Query(24, ge=1, le=720), 
    date: str | None = Query(None), 
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    response: Response = None,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    is_admin = current_user and current_user.role == "admin"
    cache_key = f"stats_{hours}_{date}_{start_date}_{end_date}_{is_admin}"
    cached = cache.get(cache_key)
    if cached:
        if response: response.headers["Cache-Control"] = "public, max-age=120"
        return cached

    if start_date or end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.min
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) if end_date else datetime.max
        except ValueError:
            start = datetime.utcnow() - timedelta(hours=hours)
            end = datetime.utcnow()
    elif date:
        try:
            target = datetime.strptime(date, "%Y-%m-%d")
            start = target.replace(hour=0, minute=0, second=0)
            end = start + timedelta(days=1)
        except ValueError:
             start = datetime.utcnow() - timedelta(hours=hours)
             end = datetime.utcnow()
    else:
        start = datetime.utcnow() - timedelta(hours=hours)
        end = datetime.utcnow()

    # 1. New articles count (total signals)
    total_articles = db.query(func.count(Article.id)).filter(
        Article.published_at >= start, 
        Article.published_at < end,
        Article.status == "approved"
    ).scalar() or 0

    needs_verification_count = db.query(func.count(Article.id)).filter(
        Article.published_at >= start,
        Article.published_at < end,
        Article.status == "approved",
        Article.needs_verification == 1
    ).scalar() or 0

    # 2. Events Aggregation
    events_q = db.query(Event).filter(
        Event.started_at >= start, 
        Event.started_at < end,
        Event.disaster_type.notin_(["unknown", "other"]),
        Event.sources_count > 0
    )
    
    if not is_admin:
        from sqlalchemy import or_
        events_q = events_q.filter(or_(
            Event.confidence >= 0.8,
            (Event.needs_verification == 0) & (Event.sources_count >= 2)
        ))

    # Calculate Aggregates using SQL
    from sqlalchemy.sql import case
    
    # Counts by distinct provinces
    # SQLAlchemy doesn't support count(distinct) cleanly in all dialects without func, but usually fine
    provinces_count = db.query(func.count(func.distinct(Event.province))).filter(
        Event.started_at >= start, 
        Event.started_at < end,
        Event.disaster_type.notin_(["unknown", "other"]),
        Event.sources_count > 0,
        Event.province.in_(PROVINCES) # Only count valid provinces
    )
    if not is_admin:
        # Re-apply filter for public
        from sqlalchemy import or_
        provinces_count = provinces_count.filter(or_(
            Event.confidence >= 0.8,
            (Event.needs_verification == 0) & (Event.sources_count >= 2)
        ))
    provinces_count = provinces_count.scalar() or 0

    # Events Count and Impacts
    # We aggregate: count, sum(deaths), sum(missing), sum(injured), count_human_impact, count_property_impact
    
    # For counts with conditions, we use case
    human_damage_case = case(
        ( (func.coalesce(Event.deaths, 0) + func.coalesce(Event.missing, 0) + func.coalesce(Event.injured, 0)) > 0, 1),
        else_=0
    )
    
    # Rough property damage check (billions > 0)
    prop_damage_case = case(
        ( func.coalesce(Event.damage_billion_vnd, 0) > 0, 1 ),
        else_=0
    )

    columns = [
        func.count(Event.id),
        func.sum(func.coalesce(Event.deaths, 0)),
        func.sum(func.coalesce(Event.missing, 0)),
        func.sum(func.coalesce(Event.injured, 0)),
        func.sum(human_damage_case),
        func.sum(prop_damage_case)
    ]
    
    # Reuse the same filter base logic for aggregation
    agg_q = db.query(*columns).filter(
        Event.started_at >= start, 
        Event.started_at < end,
        Event.disaster_type.notin_(["unknown", "other"]),
        Event.sources_count > 0
    )
    if not is_admin:
        from sqlalchemy import or_
        agg_q = agg_q.filter(or_(
            Event.confidence >= 0.8,
            (Event.needs_verification == 0) & (Event.sources_count >= 2)
        ))
        
    agg_res = agg_q.first()
    
    events_count = agg_res[0] or 0
    total_deaths = agg_res[1] or 0
    total_missing = agg_res[2] or 0
    total_injured = agg_res[3] or 0
    events_human_damage = agg_res[4] or 0
    events_property_damage = agg_res[5] or 0

    # Type breakdown
    type_counts_q = db.query(Event.disaster_type, func.count(Event.id)).filter(
        Event.started_at >= start, 
        Event.started_at < end,
        Event.disaster_type.notin_(["unknown", "other"]),
        Event.sources_count > 0
    )
    if not is_admin:
        from sqlalchemy import or_
        type_counts_q = type_counts_q.filter(or_(
            Event.confidence >= 0.8,
            (Event.needs_verification == 0) & (Event.sources_count >= 2)
        ))
    
    type_counts_rows = type_counts_q.group_by(Event.disaster_type).all()
    
    official_types = [
        "storm", "flood", "flash_flood", "landslide", "subsidence", 
        "drought", "salinity", "extreme_weather", "heatwave", "cold_surge",
        "earthquake", "tsunami", "storm_surge", "wildfire",
        "warning_forecast", "recovery"
    ]
    type_counts = {t: 0 for t in official_types}
    type_counts["unknown"] = 0
    
    for row in type_counts_rows:
        dtype, cnt = row
        if dtype in type_counts:
            type_counts[dtype] += cnt
        else:
            type_counts["unknown"] += cnt # Should be 0 since we filtered unknown

    # Top Provinces breakdown (for hotspots) (Limit to top 20)
    prov_counts_q = db.query(Event.province, func.count(Event.id)).filter(
        Event.started_at >= start, 
        Event.started_at < end,
        Event.disaster_type.notin_(["unknown", "other"]),
        Event.sources_count > 0,
        Event.province.in_(PROVINCES)
    )
    if not is_admin:
        from sqlalchemy import or_
        prov_counts_q = prov_counts_q.filter(or_(
            Event.confidence >= 0.8,
            (Event.needs_verification == 0) & (Event.sources_count >= 2)
        ))
    
    prov_counts_rows = prov_counts_q.group_by(Event.province).order_by(func.count(Event.id).desc()).limit(20).all()
    by_province = [{"province": row[0], "events": row[1]} for row in prov_counts_rows]

    res = {
        "window_hours": hours if not date else 24,
        "window_label": f"Ngày {date}" if date else f"Trong {hours}h qua",
        "articles_count": total_articles,
        "events_with_human_damage": int(events_human_damage),
        "events_with_property_damage": int(events_property_damage),
        "needs_verification_count": needs_verification_count,
        "events_count": events_count,
        "provinces_count": provinces_count,
        "impacts": {
            "deaths": int(total_deaths),
            "missing": int(total_missing),
            "injured": int(total_injured)
        },
        "by_type": type_counts,
        "by_province": by_province,
    }
    cache.set(cache_key, res, ttl=120)
    from fastapi import Response
    # Cache summary for 2 mins (same as internal cache)
    if response: response.headers["Cache-Control"] = "public, max-age=120"
    return res

@router.get("/stats/timeline")
def stats_timeline(
    response: Response,
    hours: int = Query(24, ge=1, le=168), 
    date: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Timeline: số sự kiện theo giờ."""
    cache_key = f"timeline_{hours}_{date}_{start_date}_{end_date}"
    cached = cache.get(cache_key)
    if cached: 
        response.headers["Cache-Control"] = "public, max-age=180"
        return cached

    if start_date or end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.min
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) if end_date else datetime.max
        except ValueError:
            start = datetime.utcnow() - timedelta(hours=hours)
            end = datetime.utcnow()
    elif date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        except ValueError:
            start = datetime.utcnow() - timedelta(hours=hours)
            end = datetime.utcnow()
    else:
        start = datetime.utcnow() - timedelta(hours=hours)
        end = datetime.utcnow()
    
    # Database agnostic hour grouping
    if engine.url.drivername.startswith("postgresql"):
        time_func = func.date_trunc('hour', Event.started_at)
    else:
        time_func = func.strftime('%Y-%m-%d %H:00:00', Event.started_at)

    query = db.query(
        time_func.label('hour'),
        func.count(Event.id).label('count')
    ).filter(Event.started_at >= start, Event.started_at < end).group_by(
        'hour'
    ).order_by('hour')
    
    results = {row[0]: row[1] for row in query.all()}
    
    # Fill gaps for 24h view if on a single date
    data = []
    if date:
        for i in range(24):
            h_str = (start + timedelta(hours=i)).strftime('%Y-%m-%d %H:00:00')
            # For Postgres, the key might be a datetime object
            found = False
            for k, v in results.items():
                k_str = k.strftime('%Y-%m-%d %H:00:00') if hasattr(k, 'strftime') else str(k)
                if k_str == h_str:
                    data.append({"time": h_str, "events": v})
                    found = True
                    break
            if not found:
                data.append({"time": h_str, "events": 0})
    else:
        for hour, count in query.all():
            h_str = hour.strftime('%Y-%m-%d %H:00:00') if hasattr(hour, 'strftime') else str(hour)
            data.append({"time": h_str, "events": count})
    
    response.headers["Cache-Control"] = "public, max-age=300"
    return {"window": date or f"{hours}h", "data": data}


@router.get('/stream/events')
async def stream_events(request: Request):
    """Server-Sent Events endpoint streaming new events as they are published."""
    q = broadcast.subscribe()

    async def event_publisher():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await q.get()
                    yield f"data: {msg}\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            broadcast.unsubscribe(q)

    return StreamingResponse(event_publisher(), media_type='text/event-stream')


from .auth import get_current_admin

@router.get('/admin/skip-logs')
def get_skip_logs(limit: int = Query(200, ge=1, le=5000), admin: models.User = Depends(get_current_admin)):
    logs_dir = Path(__file__).resolve().parents[1] / 'logs'
    log_file = logs_dir / 'review_potential_disasters.jsonl'
    out = []
    if not log_file.exists():
        return []
    try:
        with log_file.open('r', encoding='utf-8') as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return out[-limit:]


@router.post('/admin/label')
def label_log(payload: dict, admin: models.User = Depends(get_current_admin)):
    """Label a skipped/accepted item for training/audit. Payload must include `id` and `label`."""
    logs_dir = Path(__file__).resolve().parents[1] / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    labels_file = logs_dir / 'labels.jsonl'
    record = {
        'timestamp': datetime.utcnow().isoformat(),
        'entry': payload,
    }
    try:
        with labels_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    return {'ok': True}


@router.get('/admin/pending-articles')
def get_pending_articles(
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db), 
    admin: models.User = Depends(get_current_admin)
):
    """Fetch articles waiting for admin review."""
    return db.query(models.Article).filter(models.Article.status == "pending")\
             .order_by(models.Article.published_at.desc())\
             .offset(skip).limit(limit).all()


@router.post('/admin/approve-article/{article_id}')
async def approve_article(article_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    """Approve a pending article and integrate it into events."""
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    article.status = "approved"
    # Update events
    upsert_event_for_article(db, article)
    db.commit()
    # Invalidate event detail cache
    if article.event_id:
        cache.delete(f"ev_detail_{article.event_id}")
    return {"ok": True, "message": "Article approved and event updated"}


@router.post('/admin/events/{event_id}/approve')
async def approve_event(event_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    """Approve an entire event: clear needs_verification and approve all articles."""
    ev = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    ev.needs_verification = 0
    # Also approve all pending articles in this event
    db.query(models.Article).filter(
        models.Article.event_id == event_id,
        models.Article.status == "pending"
    ).update({"status": "approved"}, synchronize_session=False)
    
    db.commit()
    # Invalidate cache
    cache.delete(f"ev_detail_{event_id}")
    cache.delete_match("stats_*")
    
    return {"ok": True, "message": "Event and its articles approved"}


@router.post('/admin/reject-article/{article_id}')
async def reject_article(article_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    """Reject an article and add its hash to blacklist to prevent re-crawling."""
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    article.status = "rejected"
    
    # Add to blacklist if hash exists
    if article.news_hash:
        blacklist_entry = models.Blacklist(
            news_hash=article.news_hash,
            title=article.title,
            reason="Admin explicit rejection"
        )
        # Avoid duplicate blacklist entries
        existing = db.query(models.Blacklist).filter(models.Blacklist.news_hash == article.news_hash).first()
        if not existing:
            db.add(blacklist_entry)
            
    db.commit()
    return {"ok": True, "message": "Article rejected and blacklisted"}


@router.post('/alerts')
def post_alert(payload: dict):
    """Receive an alert to be pushed to subscribers or external push systems.
    This stores the alert in `logs/alerts.jsonl` and publishes it to SSE subscribers.
    """
    logs_dir = Path(__file__).resolve().parents[1] / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    alerts_file = logs_dir / 'alerts.jsonl'
    record = {'timestamp': datetime.utcnow().isoformat(), 'alert': payload}
    try:
        with alerts_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        # publish to subscribers
        try:
            asyncio.create_task(broadcast.publish_event({'type': 'alert', 'alert': payload}))
        except Exception:
            pass
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    return {'ok': True}

@router.get("/stats/heatmap")
def stats_heatmap(
    hours: int = Query(24, ge=1, le=168), 
    date: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Heatmap: số sự kiện theo tỉnh"""
    if start_date or end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.min
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) if end_date else datetime.max
        except ValueError:
            start = datetime.utcnow() - timedelta(hours=hours)
            end = datetime.utcnow()
    elif date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        except ValueError:
            start = datetime.utcnow() - timedelta(hours=hours)
            end = datetime.utcnow()
    else:
        start = datetime.utcnow() - timedelta(hours=hours)
        end = datetime.utcnow()

    # Fetch and filter events using unified logic
    events = db.query(Event).filter(Event.started_at >= start, Event.started_at < end).all()
    filtered_events = filter_disaster_events(events)
    
    prov_counts = {}
    for ev in filtered_events:
        p = ev.province or "unknown"
        if p in PROVINCES:
            prov_counts[p] = prov_counts.get(p, 0) + 1
            
    # Sort and format
    sorted_data = sorted(prov_counts.items(), key=lambda x: x[1], reverse=True)
    data = [{"province": p, "events": c} for p, c in sorted_data]
    
    return {"hours": hours, "data": data}

@router.get("/stats/top-risky-province")
def top_risky_province(
    hours: int = Query(24, ge=1, le=168),
    date: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Tỉnh nguy hiểm nhất"""
    if start_date or end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.min
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) if end_date else datetime.max
        except ValueError:
            start = datetime.utcnow() - timedelta(hours=hours)
            end = datetime.utcnow()
    elif date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        except ValueError:
            start = datetime.utcnow() - timedelta(hours=hours)
            end = datetime.utcnow()
    else:
        start = datetime.utcnow() - timedelta(hours=hours)
        end = datetime.utcnow()
    
    query = db.query(
        Event.province,
        func.count(Event.id).label('count'),
        func.max(Event.last_updated_at).label('latest')
    ).filter(
        Event.started_at >= start,
        Event.started_at < end,
        Event.province != 'unknown'
    ).group_by(Event.province).order_by(desc(func.count(Event.id)), desc(func.max(Event.last_updated_at))).limit(1)
    
    result = query.first()
    if result:
        return {
            "province": result[0],
            "events_24h": result[1],
            "latest_update": result[2]
        }
    return {"province": "Chưa có", "events_24h": 0, "latest_update": None}
@router.get("/stats/sources-health")
def sources_health():
    """Returns the latest report from the SourceMonitor."""
    logs_dir = Path(__file__).resolve().parents[1] / 'logs'
    report_file = logs_dir / 'source_status.json'
    
    # Look for logs in both possible locations (dev and docker)
    try:
        if not report_file.exists():
            backend_dir = Path(__file__).resolve().parents[1]
            report_file = backend_dir / 'logs' / 'source_status.json'
            
        if not report_file.exists():
            return {"error": "Report not generated yet."}
            
        with report_file.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to read report: {str(e)}"}

@router.get("/admin/crawler-status")
def get_crawler_status(db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    return db.query(CrawlerStatus).all()

@router.post("/admin/ai-feedback")
async def submit_ai_feedback(payload: dict, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    article_id = payload.get("article_id")
    corrected_type = payload.get("corrected_type")
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    feedback = AiFeedback(
        article_id=article_id,
        user_id=admin.id,
        original_type=article.disaster_type,
        corrected_type=corrected_type,
        comment=payload.get("comment")
    )
    db.add(feedback)
    
    # Actually update the article as well (manual override)
    article.disaster_type = corrected_type
    
    db.commit()
    return {"ok": True, "message": "Feedback saved and classification updated."}

@router.get("/admin/export/event/{event_id}")
async def export_event_data(event_id: int, format: str = "excel", db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    import pandas as pd
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    articles = db.query(Article).filter(Article.event_id == event_id).all()
    
    # Disaster type mapping for Vietnamese names
    TYPE_MAP = {
        "storm": "Bão/ATND",
        "flood": "Lũ, ngập lụt",
        "landslide": "Sạt lở đất",
        "flash_flood": "Lũ quét",
        "wildfire": "Cháy rừng",
        "drought": "Hạn hán",
        "salinity": "Xâm nhập mặn",
        "quake_tsunami": "Động đất/Sóng thần",
        "extreme_weather": "Mưa lớn/Lốc/Sét",
        "cold_surge": "Rét hại/Sương muối",
        "heatwave": "Nắng nóng",
    }
    
    data = []
    for art in articles:
        # Construct summary damage description
        damage_desc = []
        if art.deaths or art.missing or art.injured:
            damage_desc.append(f"{art.deaths or 0} người chết, {art.missing or 0} mất tích, {art.injured or 0} bị thương.")
        if art.damage_billion_vnd:
            damage_desc.append(f"Thiệt hại khoảng {art.damage_billion_vnd} tỷ VNĐ.")
        if art.summary:
            damage_desc.append(art.summary)
        
        row = {
            "Loại hình thiên tai": TYPE_MAP.get(art.disaster_type, art.disaster_type),
            "Thời gian": (art.event_time or art.published_at).strftime("%d/%m/%Y"),
            "Ngày đăng tin": art.published_at.strftime("%d/%m/%Y"),
            "Tuyến đường": art.route or "",
            "Vị trí thôn/bản": art.village or "",
            "Xã": art.commune or "",
            "Tỉnh": art.province or "",
            "Nguyên nhân (mưa hay hoạt động nhân sinh)": art.cause or "",
            "Mô tả đặc điểm trượt lở": art.characteristics or "",
            "Mô tả thiệt hại": " ".join(damage_desc),
            "Hình ảnh": art.image_url or "",
            "Nguồn": art.url
        }
        data.append(row)
        
    df = pd.DataFrame(data)
    
    if format == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Chi tiết thiệt hại')
        output.seek(0)
        
        headers = {'Content-Disposition': f'attachment; filename="bao-cao-thiet-hai-event-{event_id}.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    elif format == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Try to use a font that supports Vietnamese if available, otherwise fallback
        # This is a bit tricky in a generic environment, but we'll try basic Helvetica first
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"BAO CAO THIET HAI SU KIEN: {ev.title}", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Thoi gian bat dau: {ev.started_at.strftime('%Y-%m-%d')}", styles['Normal']))
        elements.append(Paragraph(f"Loai thien tai: {ev.disaster_type} | Tinh thanh: {ev.province}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Table data
        table_data = [["Ngay", "Nguon", "Tieu de", "Tu vong", "Mat tich", "Bi thuong", "Thiet hai"]]
        for art in articles:
            # Strip accents for PDF if font support is unreliable (simplified for this task)
            # Actually we'll just use the raw text and hope for the best or use a standard font
            table_data.append([
                art.published_at.strftime("%d/%m"),
                art.source[:15],
                art.title[:50] + "...",
                str(art.deaths or 0),
                str(art.missing or 0),
                str(art.injured or 0),
                str(art.damage_billion_vnd or 0)
            ])
            
        t = Table(table_data, colWidths=[50, 80, 400, 50, 50, 50, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        
        doc.build(elements)
        buffer.seek(0)
        headers = {'Content-Disposition': f'attachment; filename="bao-cao-thiet-hai-event-{event_id}.pdf"'}
        return StreamingResponse(buffer, headers=headers, media_type='application/pdf')

@router.get("/admin/export/daily")
async def export_daily_summary(date: str = None, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    import pandas as pd
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
        
    target_date = datetime.strptime(date, "%Y-%m-%d")
    start = target_date.replace(hour=0, minute=0, second=0)
    end = start + timedelta(days=1)
    
    events = db.query(Event).filter(Event.started_at >= start, Event.started_at < end).all()
    
    data = []
    for ev in events:
        data.append({
            "ID": ev.id,
            "Tên sự kiện": ev.title,
            "Loại": ev.disaster_type,
            "Tỉnh": ev.province,
            "Bắt đầu": ev.started_at.strftime("%Y-%m-%d %H:%M"),
            "Nguồn tin": ev.sources_count,
            "Tử vong": ev.deaths or 0,
            "Mất tích": ev.missing or 0,
            "Bị thương": ev.injured or 0,
            "Thiệt hại (Tỷ VNĐ)": ev.damage_billion_vnd or 0
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=f'Báo cáo {date}')
    output.seek(0)
    
    headers = {'Content-Disposition': f'attachment; filename="bao-cao-ngay-{date}.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
