import sys
import os
from sqlalchemy import create_engine, text
from app.database import SessionLocal

def count_articles():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM articles"))
        count = result.scalar()
        print(f"Total articles in database: {count}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    count_articles()
