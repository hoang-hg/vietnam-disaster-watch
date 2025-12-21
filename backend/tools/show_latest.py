import sys
import os
from sqlalchemy import create_engine, text
from app.database import SessionLocal
from app.models import Article

def show_latest():
    db = SessionLocal()
    try:
        # Lấy 10 bài viết có ID lớn nhất (vừa được thêm vào sau cùng)
        result = db.execute(text("SELECT id, title, source, fetched_at FROM articles ORDER BY id DESC LIMIT 15"))
        rows = result.fetchall()
        
        print(f"--- 10 BÀI VIẾT MỚI NHẤT TRONG DATABASE ---")
        for row in rows:
            # row is tuple-like
            print(f"[ID: {row[0]}] {row[2]}: {row[1]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    show_latest()
