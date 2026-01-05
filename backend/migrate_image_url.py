from sqlalchemy import text
from app.database import engine

def migrate():
    with engine.connect() as conn:
        print(f"Checking columns in {engine.url.drivername}...")
        
        # Check tables and add image_url if missing
        for table in ["articles", "events"]:
            try:
                # Add image_url to table if it doesn't exist
                if engine.url.drivername.startswith("postgresql"):
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS image_url TEXT"))
                else:
                    # SQLite doesn't support ADD COLUMN IF NOT EXISTS
                    # We try to add it and ignore error if it exists
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN image_url TEXT"))
                        print(f"Added image_url to {table}")
                    except Exception as e:
                        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                            print(f"Column image_url already exists in {table}")
                        else:
                            raise e
                conn.commit()
                print(f"Ensured image_url in {table}")
            except Exception as e:
                print(f"Error migrating {table}: {e}")

if __name__ == "__main__":
    migrate()
