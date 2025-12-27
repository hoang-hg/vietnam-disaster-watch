from app.database import SessionLocal
from app.models import Event, Article
from app.cache import cache

def cleanup_ghost_events():
    db = SessionLocal()
    try:
        events = db.query(Event).all()
        deleted_count = 0
        for e in events:
            # Count articles that are NOT rejected
            active_articles = db.query(Article).filter(
                Article.event_id == e.id,
                Article.status != "rejected"
            ).all()
            
            article_count = len(active_articles)
            
            if article_count == 0:
                db.delete(e)
                deleted_count += 1
            else:
                # Sync sources_count if it's wrong
                actual_sources = len(set(a.source for a in active_articles))
                if e.sources_count != actual_sources:
                    e.sources_count = actual_sources
        
        db.commit()
        if deleted_count > 0:
            if cache:
                cache.delete_match("ev_v2_*")
                cache.delete_match("stats_*")
        print(f"Successfully deleted {deleted_count} ghost events (events with 0 articles).")
    except Exception as err:
        print(f"Error during cleanup: {err}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_ghost_events()
