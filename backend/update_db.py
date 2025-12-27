from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        print("Migrating database...")
        try:
            conn.execute(text("ALTER TABLE crowdsourced_reports ADD COLUMN IF NOT EXISTS name VARCHAR(255);"))
            conn.execute(text("ALTER TABLE crowdsourced_reports ADD COLUMN IF NOT EXISTS phone VARCHAR(20);"))
            conn.execute(text("ALTER TABLE crowdsourced_reports ADD COLUMN IF NOT EXISTS address TEXT;"))
            conn.execute(text("ALTER TABLE crowdsourced_reports ALTER COLUMN user_id DROP NOT NULL;"))
            conn.commit()
            print("Migration successful")
        except Exception as e:
            print(f"Migration failed (columns might already exist): {e}")

if __name__ == "__main__":
    migrate()
