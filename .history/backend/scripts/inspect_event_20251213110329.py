#!/usr/bin/env python
"""Debug helper: inspect an event and run NLP extraction on its articles.

Run from repository root with:
  cd backend
  python .\scripts\inspect_event.py --event 1

"""
import argparse
import sys
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=int, required=True, help="Event ID to inspect")
    args = parser.parse_args()

    # Ensure we can import the package when run from backend dir
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))

    from app.database import SessionLocal, engine
    from app.models import Event, Article
    from app import nlp

    session = SessionLocal()
    try:
        ev = session.query(Event).filter(Event.id == args.event).one_or_none()
        if not ev:
            print(f"Event id={args.event} not found")
            raise SystemExit(2)

        print("\n=== Event ===")
        print(f"id: {ev.id}")
        print(f"title: {ev.title}")
        print(f"disaster_type: {ev.disaster_type}")
        print(f"province: {ev.province}")
        print(f"started_at: {ev.started_at}")
        print(f"last_updated_at: {ev.last_updated_at}")
        print(f"deaths: {ev.deaths}")
        print(f"missing: {ev.missing}")
        print(f"injured: {ev.injured}")
        print(f"damage_billion_vnd: {ev.damage_billion_vnd}")
        print(f"confidence: {ev.confidence}")
        print(f"sources_count: {ev.sources_count}")

        print("\n=== Articles ===")
        arts = session.query(Article).filter(Article.event_id == ev.id).order_by(Article.published_at.desc()).all()
        if not arts:
            print("(no articles for this event)")
        for a in arts:
            print('\n---')
            print(f"article id: {a.id}")
            print(f"source: {a.source} | domain: {a.domain}")
            print(f"published_at: {a.published_at}")
            print(f"title: {a.title}")
            print(f"stored summary: {a.summary!r}")
            print(f"stored extracted - deaths:{a.deaths} missing:{a.missing} injured:{a.injured} damage:{a.damage_billion_vnd} agency:{a.agency}")

            txt = "".join([s for s in [a.title or "", "\n", a.summary or ""]])
            print("\n-> Running nlp.extract_impacts on combined title+summary:\n")
            out = nlp.extract_impacts(txt)
            print(out)
            # also show province extraction and summary cleaning
            prov = nlp.extract_province(txt)
            print(f"-> extract_province: {prov}")
            print(f"-> summarize: {nlp.summarize(txt)[:300]!r}")

    finally:
        session.close()
