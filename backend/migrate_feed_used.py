from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        print("Checking for feed_used column in crawler_status table...")
        try:
            conn.execute(text("ALTER TABLE crawler_status ADD COLUMN feed_used VARCHAR(255)"))
            conn.commit()
            print("Successfully added column 'feed_used' to 'crawler_status' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column 'feed_used' already exists.")
            else:
                print(f"Error migrating: {e}")

if __name__ == "__main__":
    migrate()
