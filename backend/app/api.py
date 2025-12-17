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
    type: str | None = Query(None),
    province: str | None = Query(None),
    start_date: str | None = Query(None, description="Format: YYYY-MM-DD"),
    end_date: str | None = Query(None, description="Format: YYYY-MM-DD"),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Event).order_by(desc(Event.last_updated_at))
    
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
        
    return query.limit(limit).all()

@router.get("/events/{event_id}", response_model=EventDetailOut)
def event_detail(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).one()
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
    
    total_articles = db.query(Article).filter(Article.published_at >= start, Article.published_at < end).count()
    total_events = db.query(Event).filter(Event.last_updated_at >= start, Event.last_updated_at < end).count()

    types = ["storm", "flood", "landslide", "earthquake", "tsunami", "wind_hail", "wildfire", "extreme_weather", "unknown"]
    by_type = {t: db.query(Event).filter(Event.last_updated_at >= start, Event.last_updated_at < end, Event.disaster_type == t).count() for t in types}

    return {
        "window_hours": hours,
        "articles_24h": total_articles,
        "events_24h": total_events,
        "by_type": by_type,
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
