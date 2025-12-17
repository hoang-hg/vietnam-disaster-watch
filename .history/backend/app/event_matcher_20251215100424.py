from datetime import datetime
from sqlalchemy.orm import Session
from .models import Article, Event
from . import broadcast

def _bucket_day(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def make_event_key(article: Article) -> str:
    day = _bucket_day(article.published_at)
    return f"{article.disaster_type}|{article.province}|{day}"

def upsert_event_for_article(db: Session, article: Article) -> Event:
    key = make_event_key(article)
    ev = db.query(Event).filter(Event.key == key).one_or_none()

    if ev is None:
        ev = Event(
            key=key,
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
            # publish minimal event info asynchronously
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

    ev.last_updated_at = max(ev.last_updated_at, article.published_at)

    for field in ["deaths", "missing", "injured"]:
        val = getattr(article, field)
        if val is not None:
            cur = getattr(ev, field)
            setattr(ev, field, max(cur or 0, val))
    if article.damage_billion_vnd is not None:
        ev.damage_billion_vnd = max(ev.damage_billion_vnd or 0.0, article.damage_billion_vnd)

    sources = {a.source for a in ev.articles} | {article.source}
    ev.sources_count = len(sources)
    if ev.sources_count == 1:
        ev.confidence = 0.25
    elif ev.sources_count == 2:
        ev.confidence = 0.50
    elif ev.sources_count == 3:
        ev.confidence = 0.75
    else:
        ev.confidence = 0.9

    article.event_id = ev.id
    return ev
