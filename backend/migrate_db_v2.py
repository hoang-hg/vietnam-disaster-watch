import sqlite3
import os
from app.settings import settings

def migrate():
    db_url = settings.app_db_url
    if not db_url.startswith("sqlite:///"):
        print("Not using SQLite, skipping automatic migration script.")
        print("Please run: ALTER TABLE users ADD COLUMN favorite_province VARCHAR(64);")
        print("Please run: ALTER TABLE users ADD COLUMN email_notifications BOOLEAN DEFAULT 1;")
        # ... and so on for other columns
        return

    db_path = db_url.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}. It will be created on first start.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # User table migrations
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN favorite_province VARCHAR(64)")
        print("Added favorite_province to users")
    except sqlite3.OperationalError:
        print("favorite_province already exists in users")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email_notifications BOOLEAN DEFAULT 1")
        print("Added email_notifications to users")
    except sqlite3.OperationalError:
        print("email_notifications already exists in users")

    # Event table migrations
    cols_to_add = [
        ("commune", "VARCHAR(128)"),
        ("village", "VARCHAR(128)"),
        ("route", "VARCHAR(128)"),
        ("cause", "TEXT"),
        ("characteristics", "TEXT")
    ]
    
    for col_name, col_type in cols_to_add:
        try:
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} to events")
        except sqlite3.OperationalError:
            print(f"{col_name} already exists in events")

    # Article table also got new columns in previous steps, let's ensure they are there too
    article_cols = [
        ("commune", "VARCHAR(128)"),
        ("village", "VARCHAR(128)"),
        ("route", "VARCHAR(128)"),
        ("cause", "TEXT"),
        ("characteristics", "TEXT")
    ]
    for col_name, col_type in article_cols:
        try:
            cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} to articles")
        except sqlite3.OperationalError:
            print(f"{col_name} already exists in articles")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
