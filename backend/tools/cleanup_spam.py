import sys
import os
from sqlalchemy import create_engine, text
from app.settings import settings
from app.database import SessionLocal
from app.models import Article
from app.nlp import DISASTER_NEGATIVE

def cleanup_spam_articles():
    db = SessionLocal()
    try:
        print("Scanning for spam articles using new filters...")
        
        # Compile a simplified list of SQL ILIKE patterns from DISASTER_NEGATIVE regexes
        # Note: Converting Python Regex to SQL LIKE is tricky. 
        # Instead, we fetch recent articles (e.g. last 7 days) and re-check with Python NLP
        
        # Or simpler: Delete by specific keywords identified in user report
        keywords = [
            "%mại dâm%", "%bán dâm%", "%mua dâm%", "%môi giới%",
        ]
        
        total_deleted = 0
        
        # 1. Delete by explicit keywords (Fastest)
        for kw in keywords:
            # Check title or summary
            stmt = text("DELETE FROM articles WHERE title ILIKE :kw OR summary ILIKE :kw")
            result = db.execute(stmt, {"kw": kw})
            if result.rowcount > 0:
                print(f"Deleted {result.rowcount} articles matching '{kw}'")
                total_deleted += result.rowcount
            
        # 2. Advanced: Re-scan recent articles with Python NLP
        # (Useful for complex regexes that SQL can't handle easily)
        print("\nRe-scanning recent articles with Python NLP rules...")
        import re
        from app.nlp import classify_disaster # Re-import to get latest rules
        
        # Get articles from last 3 days
        articles = db.query(Article).order_by(Article.id.desc()).limit(500).all()
        
        count_nlp = 0
        for art in articles:
            content = (art.title + " " + (art.summary or "")).lower()
            
            # Check against updated HARD_NEGATIVE list in nlp.py
            is_spam = False
            for pattern in DISASTER_NEGATIVE:
                if re.search(pattern, content, flags=re.IGNORECASE):
                    print(f"[SPAM DETECTED] {art.id} - {art.title[:50]}...")
                    is_spam = True
                    break
            
            if is_spam:
                db.delete(art)
                count_nlp += 1
        
        if count_nlp > 0:
            print(f"Deleted {count_nlp} articles detected by NLP re-scan.")
            total_deleted += count_nlp

        db.commit()
        print(f"\n✅ Cleanup Complete. Total deleted: {total_deleted}")
        
    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure current directory is in python path to resolve 'app'
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cleanup_spam_articles()
