#!/usr/bin/env python
"""List events and articles that already have non-null impact fields.

Usage:
  cd backend
  python .\scripts\list_impacted_events.py
"""
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "backend"))

from app.database import SessionLocal
from app.models import Event, Article


def main():
    session = SessionLocal()
    try:
        evq = session.query(Event).filter(
            (Event.deaths != None) | (Event.missing != None) | (Event.injured != None) | (Event.damage_billion_vnd != None)
        ).order_by(Event.last_updated_at.desc())
        events = evq.limit(50).all()
        print(f"Events with any impacts set: {len(events)}")
        for ev in events:
            print("---")
            print(f"event id: {ev.id} title: {ev.title[:80]!r}")
            print(f"deaths:{ev.deaths} missing:{ev.missing} injured:{ev.injured} damage:{ev.damage_billion_vnd}")
            arts = session.query(Article).filter(Article.event_id == ev.id).limit(5).all()
            for a in arts:
                print(f"  article id:{a.id} src:{a.source} title:{(a.title or '')[:80]!r} deaths:{a.deaths} missing:{a.missing} injured:{a.injured} damage:{a.damage_billion_vnd}")

    finally:
        session.close()


if __name__ == '__main__':
    main()
