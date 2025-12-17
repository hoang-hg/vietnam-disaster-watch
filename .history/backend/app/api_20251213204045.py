from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
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
def stats_summary(db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=24)
    total_articles_24h = db.query(Article).filter(Article.published_at >= since).count()
    total_events_24h = db.query(Event).filter(Event.last_updated_at >= since).count()

    types = ["storm", "flood", "landslide", "earthquake", "tsunami", "wind_hail", "wildfire", "extreme_weather", "unknown"]
    by_type = {t: db.query(Article).filter(Article.published_at >= since, Article.disaster_type == t).count() for t in types}

    return {
        "window_hours": 24,
        "articles_24h": total_articles_24h,
        "events_24h": total_events_24h,
        "by_type": by_type,
    }
