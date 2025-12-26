from sqlalchemy import create_engine, text
from app.settings import settings

def migrate():
    engine = create_engine(settings.app_db_url)
    
    with engine.connect() as conn:
        # User table
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN favorite_province VARCHAR(64)"))
            print("Added favorite_province to users")
        except Exception as e:
            print(f"User province skip: {e}")

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN email_notifications BOOLEAN DEFAULT TRUE"))
            print("Added email_notifications to users")
        except Exception as e:
            print(f"User email skip: {e}")

        # Event table
        for col in ["commune", "village", "route"]:
            try:
                conn.execute(text(f"ALTER TABLE events ADD COLUMN {col} VARCHAR(128)"))
                print(f"Added {col} to events")
            except Exception as e:
                print(f"Event {col} skip: {e}")

        for col in ["cause", "characteristics"]:
            try:
                conn.execute(text(f"ALTER TABLE events ADD COLUMN {col} TEXT"))
                print(f"Added {col} to events")
            except Exception as e:
                print(f"Event {col} skip: {e}")

        # Article table
        for col in ["commune", "village", "route"]:
            try:
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {col} VARCHAR(128)"))
                print(f"Added {col} to articles")
            except Exception as e:
                print(f"Article {col} skip: {e}")

        for col in ["cause", "characteristics"]:
            try:
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {col} TEXT"))
                print(f"Added {col} to articles")
            except Exception as e:
                print(f"Article {col} skip: {e}")

        conn.commit()
    print("Postgres Migration finished.")

if __name__ == "__main__":
    migrate()
