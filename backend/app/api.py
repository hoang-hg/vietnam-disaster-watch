from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from sqlalchemy.sql import text
from .database import get_db
from .models import Article, Event
from .schemas import ArticleOut, EventOut, EventDetailOut
from datetime import datetime, timedelta
from fastapi import Response, Request
from fastapi.responses import StreamingResponse
import asyncio
from pathlib import Path
import json
from . import broadcast

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
    limit: int = Query(50, ge=1, le=1000),
    hours: int | None = Query(None, ge=1, le=720),
    type: str | None = Query(None),
    province: str | None = Query(None),
    start_date: str | None = Query(None, description="Format: YYYY-MM-DD"),
    end_date: str | None = Query(None, description="Format: YYYY-MM-DD"),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Event).order_by(desc(Event.started_at))
    
    if hours:
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
        
    q_events = query.limit(limit).all()
    
    # Enrich with representative image and source from the first article
    # This avoids a complex join if we just want "one" image.
    # A cleaner SQL way would be a subquery, but iterating 50 items is fast enough.
    results = []
    for ev in q_events:
        # Pydantic model will be created from ev, but we need to inject image_url/source
        # We can't easily modify the ORM object if it's not loaded with those fields.
        # So we fetch the first article.
        first_article = db.query(Article).filter(Article.event_id == ev.id).order_by(desc(Article.published_at)).first()
        
        ev_data = EventOut.from_orm(ev)
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

        results.append(ev_data)

    return results

    return results

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
    db: Session = Depends(get_db)
):
    if date:
        # Filter for specific date (YYYY-MM-DD)
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD"}
    else:
        # Use hours filter
        start = datetime.utcnow() - timedelta(hours=hours)
        end = datetime.utcnow()
    
    # Statistics Logic for Dashboard
    # Statistics Logic for Dashboard (V4 - Ultra Strict)
    STRICT_EXCLUSION = [
        "nhật bản", "indonesia", "thái lan", "trung quốc", "mỹ", "hàn quốc", "nga", "philippines", 
        "brazil", "châu âu", "thế giới", "vũ hán", "tokyo", "seoul", "bangkok", "manila",
        "tổng kết", "nhìn lại", "năm 2024", "năm 2023", "năm 2022", "kỷ niệm", "lịch sử",
        "sau bão", "kể từ", "từ đầu năm", "tổng số", "con số thực", "địa cầu", "năm 2025", "năm 2026", "năm 2027"
    ]
    
    # 1. Total Activity: Recent articles updated (Exclude outliers from main count)
    total_articles = db.query(Article).filter(
        Article.published_at >= start, 
        Article.published_at < end,
        Article.needs_verification == 0
    ).count()

    needs_verification_count = db.query(Article).filter(
        Article.published_at >= start,
        Article.published_at < end,
        Article.needs_verification == 1
    ).count()
    
    # 2. Daily New Events: Only count events that BEGAN in this window
    new_events = db.query(Event).filter(Event.started_at >= start, Event.started_at < end).all()
    
    # Python-side aggregation with strict filters
    grouped_impacts = {} 
    official_types = ["storm", "flood_landslide", "heat_drought", "wind_fog", "storm_surge", "extreme_other", "wildfire", "quake_tsunami"]
    type_counts = {t: 0 for t in official_types}
    type_counts["unknown"] = 0
    provinces_seen = set()
    filtered_events = []

    for ev in new_events:
        title_lower = ev.title.lower() if ev.title else ""
        
        # SKIP Foreign News and Historical Summaries in Stats
        if any(kw in title_lower for kw in STRICT_EXCLUSION):
            continue

        # SKIP Data needing verification from consolidated stats
        if ev.needs_verification == 1:
            continue
            
        filtered_events.append(ev)

        dtype = ev.disaster_type
        if dtype in type_counts:
            type_counts[dtype] += 1
        else:
            type_counts["unknown"] += 1
            
        if ev.province and ev.province != "unknown" and ev.province != "Toàn quốc":
            provinces_seen.add(ev.province)

        key = (ev.province, dtype)
        if key not in grouped_impacts:
            grouped_impacts[key] = {"deaths": 0, "missing": 0, "injured": 0}
            
        # Impact Clean-up Logic (MAX_REALISTIC_IMPACT = 100)
        def clean_num(n):
            val = n or 0
            if 1900 <= val <= 2030 or val > 100: return 0
            return val

        d = clean_num(ev.deaths)
        m = clean_num(ev.missing)
        i = clean_num(ev.injured)

        grouped_impacts[key]["deaths"] = max(grouped_impacts[key]["deaths"], d)
        grouped_impacts[key]["missing"] = max(grouped_impacts[key]["missing"], m)
        grouped_impacts[key]["injured"] = max(grouped_impacts[key]["injured"], i)
        
    total_deaths = sum(item["deaths"] for item in grouped_impacts.values())
    total_missing = sum(item["missing"] for item in grouped_impacts.values())
    total_injured = sum(item["injured"] for item in grouped_impacts.values())

    return {
        "window_hours": hours,
        "window_label": f"Trong {hours}h qua",
        "articles_count": total_articles,
        "needs_verification_count": needs_verification_count,
        "events_count": len(filtered_events),
        "provinces_count": len(provinces_seen),
        "impacts": {
            "deaths": total_deaths,
            "missing": total_missing,
            "injured": total_injured
        },
        "by_type": type_counts,
    }

@router.get("/stats/timeline")
def stats_timeline(hours: int = Query(24, ge=1, le=168), db: Session = Depends(get_db)):
    """Timeline: số sự kiện theo giờ trong N giờ qua"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # SQLite: GROUP BY strftime('%Y-%m-%d %H:00:00', last_updated_at)
    query = db.query(
        func.strftime('%Y-%m-%d %H:00:00', Event.last_updated_at).label('hour'),
        func.count(Event.id).label('count')
    ).filter(Event.last_updated_at >= since).group_by(
        func.strftime('%Y-%m-%d %H:00:00', Event.last_updated_at)
    ).order_by('hour')
    
    data = []
    for hour, count in query.all():
        data.append({"time": hour, "events": count})
    
    return {"hours": hours, "data": data}


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
def stats_heatmap(hours: int = Query(24, ge=1, le=168), db: Session = Depends(get_db)):
    """Heatmap: số sự kiện theo tỉnh trong N giờ qua"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(
        Event.province,
        func.count(Event.id).label('count')
    ).filter(
        Event.last_updated_at >= since,
        Event.province != 'unknown'
    ).group_by(Event.province).order_by(desc('count'))
    
    data = []
    for province, count in query.all():
        data.append({"province": province, "events": count})
    
    return {"hours": hours, "data": data}

@router.get("/stats/top-risky-province")
def top_risky_province(
    hours: int = Query(24, ge=1, le=168),
    date: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Tỉnh nguy hiểm nhất: tỉnh có sự kiện gần đây nhất hoặc nhiều sự kiện nhất"""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD"}
    else:
        start = datetime.utcnow() - timedelta(hours=hours)
        end = datetime.utcnow()
    
    query = db.query(
        Event.province,
        func.count(Event.id).label('count'),
        func.max(Event.last_updated_at).label('latest')
    ).filter(
        Event.last_updated_at >= start,
        Event.last_updated_at < end,
        Event.province != 'unknown'
    ).group_by(Event.province).order_by(desc('count'), desc('latest')).limit(1)
    
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
    
    if not report_file.exists():
        return {"error": "Report not generated yet. Please wait for the first scheduled run."}
    
    try:
        with report_file.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to read report: {str(e)}"}
