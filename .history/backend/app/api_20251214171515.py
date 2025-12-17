from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from sqlalchemy.sql import text
from .database import get_db
from .models import Article, Event
from .schemas import ArticleOut, EventOut, EventDetailOut
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/articles/latest", response_model=list[ArticleOut])
def latest_articles(
    limit: int = Query(50, ge=1, le=200),
    type: str | None = Query(None),
    province: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Article).order_by(desc(Article.published_at))
    if type:
        q = q.filter(Article.disaster_type == type)
    if province:
        q = q.filter(Article.province == province)
    return q.limit(limit).all()

@router.get("/events", response_model=list[EventOut])
def events(
    limit: int = Query(50, ge=1, le=200),
    type: str | None = Query(None),
    province: str | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Event).order_by(desc(Event.last_updated_at))
    if type:
        query = query.filter(Event.disaster_type == type)
    if province:
        query = query.filter(Event.province == province)
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
def top_risky_province(hours: int = Query(24, ge=1, le=168), db: Session = Depends(get_db)):
    """Tỉnh nguy hiểm nhất: tỉnh có sự kiện gần đây nhất hoặc nhiều sự kiện nhất"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(
        Event.province,
        func.count(Event.id).label('count'),
        func.max(Event.last_updated_at).label('latest')
    ).filter(
        Event.last_updated_at >= since,
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
