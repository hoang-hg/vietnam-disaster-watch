#!/usr/bin/env python3
"""
Clean up database by removing non-disaster articles (disaster_type='unknown').
This script helps remove articles that shouldn't have been stored in the first place.
"""

import sys
sys.path.insert(0, 'app')

from app.database import SessionLocal, engine
from app.models import Article, Event
import sqlalchemy as sa

def cleanup_database():
    """Remove all articles with disaster_type='unknown'."""
    db = SessionLocal()
    try:
        # Count articles to remove
        count_unknown = db.query(Article).filter(Article.disaster_type == 'unknown').count()
        print(f"Found {count_unknown} articles with disaster_type='unknown'")
        
        if count_unknown == 0:
            print("✓ Database is clean - no unknown disaster type articles found")
            return
        
        # Show sample articles that will be deleted
        print("\nSample articles to be deleted:")
        samples = db.query(Article).filter(Article.disaster_type == 'unknown').limit(5).all()
        for article in samples:
            print(f"  - {article.source}: {article.title[:60]}...")
        
        # Ask for confirmation
        response = input(f"\nDelete {count_unknown} articles? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Cancelled")
            return
        
        # Delete articles
        deleted = db.query(Article).filter(Article.disaster_type == 'unknown').delete()
        
        # Delete orphaned events (events with no articles)
        orphaned_events = db.query(Event).filter(
            ~Event.articles.any()
        ).delete(synchronize_session=False)
        
        db.commit()
        print(f"✓ Deleted {deleted} articles with disaster_type='unknown'")
        print(f"✓ Deleted {orphaned_events} orphaned events")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_database()
