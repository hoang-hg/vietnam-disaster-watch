import sqlite3
import os

db_path = r"D:\viet-disaster-watch\backend\data\app.db"
print(f"Testing connection to: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Success! Tables: {tables}")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
