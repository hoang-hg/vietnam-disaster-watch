from sqlalchemy import text
from app.database import engine

def migrate():
    with engine.connect() as conn:
        print("Checking/Adding 'stage' column to 'articles' table...")
        try:
            conn.execute(text("ALTER TABLE articles ADD COLUMN stage VARCHAR(32) DEFAULT 'INCIDENT';"))
            conn.execute(text("CREATE INDEX ix_articles_stage ON articles (stage);"))
            conn.commit()
            print("Successfully added 'stage' to 'articles'.")
        except Exception as e:
            conn.rollback()
            print(f"Error or already exists in articles: {e}")

        print("Checking/Adding 'stage' column to 'events' table...")
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN stage VARCHAR(32) DEFAULT 'INCIDENT';"))
            conn.execute(text("CREATE INDEX ix_events_stage ON events (stage);"))
            conn.commit()
            print("Successfully added 'stage' to 'events'.")
        except Exception as e:
            conn.rollback()
            print(f"Error or already exists in events: {e}")

if __name__ == "__main__":
    migrate()
