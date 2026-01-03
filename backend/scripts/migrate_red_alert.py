import sqlite3
import os
from pathlib import Path

def migrate():
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "data" / "app.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add is_red_alert to articles
    try:
        cursor.execute("ALTER TABLE articles ADD COLUMN is_red_alert BOOLEAN DEFAULT 0")
        print("Added is_red_alert to articles table.")
    except sqlite3.OperationalError:
        print("is_red_alert already exists in articles table.")

    # Add is_red_alert to events
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN is_red_alert BOOLEAN DEFAULT 0")
        print("Added is_red_alert to events table.")
    except sqlite3.OperationalError:
        print("is_red_alert already exists in events table.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
