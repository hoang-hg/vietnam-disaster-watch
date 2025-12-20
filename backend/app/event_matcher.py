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
                
                # Check type of first item to decide on dedup strategy
                first_item = combined[0]
                if isinstance(first_item, int):
                    # Dedup integers (casualty counts)
                    current_details[key] = sorted(list(set(combined)), reverse=True)
                elif isinstance(first_item, dict):
                    # Dedup dicts (agriculture, homes, etc)
                    # Dedupe based on 'num' + 'unit'
                    seen = set()
                    unique = []
                    for x in combined:
                        # simplistic signature: num_unit
                        # normalize unit to lower
                        u = (x.get("unit") or "").lower().strip()
                        n = x.get("num")
                        sig = f"{n}_{u}"
                        if sig not in seen:
                            seen.add(sig)
                            unique.append(x)
        ev.details = current_details



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
