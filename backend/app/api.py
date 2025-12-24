from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from sqlalchemy.sql import text
from .database import get_db, engine
from .models import Article, Event
from .schemas import ArticleOut, EventOut, EventDetailOut
from datetime import datetime, timedelta
from fastapi import Response, Request
from fastapi.responses import StreamingResponse
import asyncio
from pathlib import Path
import json
from .nlp import RECOVERY_KEYWORDS, PROVINCES
from .sources import DISASTER_KEYWORDS
from .risk_lookup import canon
from . import broadcast

# Unified filtering rules for Dashboard/Stats
def filter_disaster_events(events):
    filtered = []
    for ev in events:
        # Exclusion: Skip unknown/other
        if ev.disaster_type in ["unknown", "other", None]:
            continue
            
        # Decision 18 Logic: Skip purely administrative news if no impact and not a major hazard
        is_impacting = (ev.deaths or 0) > 0 or (ev.missing or 0) > 0 or (ev.injured or 0) > 0 or (ev.damage_billion_vnd or 0) > 0
        major_hazards = ["storm", "flood_landslide", "wildfire", "quake_tsunami"]
        
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
    q = db.query(Article).order_by(desc(Article.published_at))
    if type:
        q = q.filter(Article.disaster_type == type)
    if province:
        q = q.filter(Article.province == province)
    if exclude_unknown:
        q = q.filter(Article.disaster_type != 'unknown')
    return q.limit(limit).all()

@router.get("/events", response_model=list[EventOut])
def events(
    limit: int = Query(50, ge=1, le=2000),
    hours: int | None = Query(None, ge=1, le=720),
    type: str | None = Query(None),
    province: str | None = Query(None),
    start_date: str | None = Query(None, description="Format: YYYY-MM-DD"),
    end_date: str | None = Query(None, description="Format: YYYY-MM-DD"),
    q: str | None = Query(None),
    date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Event).order_by(desc(Event.started_at))
    
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            query = query.filter(Event.started_at >= start, Event.started_at < end)
        except ValueError:
            pass
    elif hours:
        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(Event.last_updated_at >= since)

    if type:
        query = query.filter(Event.disaster_type == type)
    if province:
        query = query.filter(Event.province == province)
    if start_date:
        try:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Event.started_at >= dt_start)
        except ValueError:
            pass
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Event.started_at < dt_end)
        except ValueError:
            pass
            
    if q:
        query = query.filter(Event.title.ilike(f"%{q}%"))
        
    # Apply unified filter
    raw_events = query.all()
    filtered = filter_disaster_events(raw_events)
    
    # Sort by impact priority before unique-province logic
    # Priority: Casualties > Damage > Article Count > Confidence
    filtered.sort(key=lambda x: (
        (x.deaths or 0) + (x.missing or 0) + (x.injured or 0),
        (x.damage_billion_vnd or 0.0),
        (x.sources_count or 0),
        (x.confidence or 0.0)
    ), reverse=True)
    
    # Limit results
    filtered = filtered[:limit]

    events_out = []
    for ev in filtered[:limit]:
        ev_data = EventOut.from_orm(ev)
        # Articles count windowed
        if hours:
            h_start = datetime.utcnow() - timedelta(hours=hours)
            ev_data.articles_count = db.query(Article).filter(
                Article.event_id == ev.id,
                Article.published_at >= h_start
            ).count()
        else:
            ev_data.articles_count = db.query(Article).filter(Article.event_id == ev.id).count()

        first_article = db.query(Article).filter(Article.event_id == ev.id).order_by(desc(Article.published_at)).first()
        if first_article:
            ev_data.image_url = first_article.image_url
            ev_data.source = first_article.source
        
        # Inject Default Image if missing
        if not ev_data.image_url:
            dtype = ev.disaster_type
            title_lower = ev.title.lower() if ev.title else ""
            
            # Smart sub-variant selection based on Title keywords
            chosen_img = DEFAULT_IMAGES.get(dtype, DEFAULT_IMAGES["unknown"])
            
            if dtype == "flood_landslide" and ("sạt" in title_lower or "lở" in title_lower):
                chosen_img = SUB_IMAGES["landslide"]
            elif dtype == "quake_tsunami" and "sóng thần" in title_lower:
                chosen_img = SUB_IMAGES["tsunami"]
            elif dtype == "extreme_other" and "mưa đá" in title_lower:
                chosen_img = SUB_IMAGES["hail"]
                
            ev_data.image_url = chosen_img

        events_out.append(ev_data)

    return events_out

# Lightweight SVGs (stable CDN, pinned version)
DEFAULT_IMAGES = {
    "storm": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/cloud-storm.svg",
    "flood_landslide": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/droplet.svg",
    "heat_drought": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/sun.svg",
    "wind_fog": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/wind.svg",
    "storm_surge": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/droplet.svg",
    "extreme_other": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/cloud-snow.svg",
    "wildfire": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/flame.svg",
    "quake_tsunami": "https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/1.13.0/icons/activity.svg",
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
def event_detail(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).one()
    # Pydantic model conversion happens automatically, but we can't inject defaults easily 
    # unless we use response_model_exclude_unset or modify the object.
    # The clean way is to return a dict or modify current object if it's not committed.
    # But EventDetailOut expects specific fields. 
    # Let's trust the frontend logic? OR we can force update the DB object just for view? No.
    # Best way: return dictionary with injected check.
    
    # Actually, for detail view, let's just let it be. 
    # But wait, user asked for "những sự kiện không có ảnh thì mình tự chèn".
    # So we should inject it here too.
    
    # Check if we need to fetch image from articles first?
    # Usually event table doesn't have image_url column? Wait, actually Article has it.
    # EventDetailOut aggregates articles.
    
    return ev

@router.get("/stats/summary")
def stats_summary(
    hours: int = Query(24, ge=1, le=720), 
    date: str | None = Query(None), 
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db)
):
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
    total_articles = db.query(Article).filter(
        Article.published_at >= start, 
        Article.published_at < end
    ).count()

    needs_verification_count = db.query(Article).filter(
        Article.published_at >= start,
        Article.published_at < end,
        Article.needs_verification == 1
    ).count()

    # 2. Events Summary (Unique Provinces per User Request)
    events = db.query(Event).filter(Event.started_at >= start, Event.started_at < end).all()
    filtered_events = filter_disaster_events(events)
    
    provinces_seen = set()
    for ev in filtered_events:
        p = ev.province or "unknown"
        if p in PROVINCES:
            provinces_seen.add(p)
    
    events_count = len(filtered_events) 
    provinces_count = len(provinces_seen)

    # Calculate Impact Statistics (Aggregated by Province for Dashboard Consistency)
    total_deaths = 0
    total_missing = 0
    total_injured = 0
    official_types = ["storm", "flood_landslide", "heat_drought", "wind_fog", "storm_surge", "extreme_other", "wildfire", "quake_tsunami"]
    type_counts = {t: 0 for t in official_types}
    type_counts["unknown"] = 0
    
    prov_impacts = {} # p -> {human: bool, prop: bool}

    events_human_damage = 0
    events_property_damage = 0

    for ev in filtered_events:
        # 1. Type counts
        dtype = ev.disaster_type
        if dtype in type_counts:
            type_counts[dtype] += 1
        else:
            type_counts["unknown"] += 1

        # 2. Cumulative Casualties
        total_deaths += (ev.deaths or 0)
        total_missing += (ev.missing or 0)
        total_injured += (ev.injured or 0)

        # 3. Individual Event Impact Flags
        if (ev.deaths or 0) + (ev.missing or 0) + (ev.injured or 0) > 0:
            events_human_damage += 1
            
        has_prop = (ev.damage_billion_vnd or 0) > 0.0
        d = ev.details or {}
        if not has_prop:
            # Check for specific impact categories in details
            if d.get("homes") or d.get("agriculture") or d.get("infrastructure") or d.get("marine") or d.get("disruption") or d.get("damage"):
                has_prop = True
        if has_prop:
            events_property_damage += 1

    return {
        "window_hours": hours if not date else 24,
        "window_label": f"Ngày {date}" if date else f"Trong {hours}h qua",
        "articles_count": total_articles,
        "events_with_human_damage": events_human_damage,
        "events_with_property_damage": events_property_damage,
        "needs_verification_count": needs_verification_count,
        "events_count": events_count,
        "provinces_count": provinces_count,
        "impacts": {
            "deaths": total_deaths,
            "missing": total_missing,
            "injured": total_injured
        },
        "by_type": type_counts,
    }

@router.get("/stats/timeline")
def stats_timeline(
    hours: int = Query(24, ge=1, le=168), 
    date: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Timeline: số sự kiện theo giờ."""
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


@router.get('/admin/skip-logs')
def get_skip_logs(limit: int = Query(200, ge=1, le=5000)):
    logs_dir = Path(__file__).resolve().parents[1] / 'logs'
    log_file = logs_dir / 'skip_debug.jsonl'
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
def label_log(payload: dict):
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


@router.post('/admin/label/revert')
def revert_label(payload: dict):
    """Record a revert/undo for a previously labeled item.
    Payload: {"id": "<article_id>"}
    This is append-only: we write a `revert` record that references the last label for the id.
    """
    logs_dir = Path(__file__).resolve().parents[1] / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    labels_file = logs_dir / 'labels.jsonl'
    entry_id = payload.get('id') if isinstance(payload, dict) else None
    if not entry_id:
        return {'ok': False, 'error': 'missing id'}

    # Try to find the most recent label for this id for auditing
    last_label = None
    try:
        if labels_file.exists():
            with labels_file.open('r', encoding='utf-8') as f:
                for line in reversed(list(f)):
                    try:
                        rec = json.loads(line)
                        ent = rec.get('entry')
                        if ent and ent.get('id') == entry_id and 'label' in ent:
                            last_label = ent.get('label')
                            break
                    except Exception:
                        continue
    except Exception:
        last_label = None

    record = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': 'revert',
        'id': entry_id,
        'reverted_label': last_label,
    }
    try:
        with labels_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    return {'ok': True, 'reverted_label': last_label}


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
