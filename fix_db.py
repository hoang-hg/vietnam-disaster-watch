import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env from backend/.env
load_dotenv(r"backend\.env")

DB_URL = os.getenv("APP_DB_URL")
if not DB_URL:
    print("APP_DB_URL not found in environment")
    exit(1)

print(f"Connecting to {DB_URL}...")
engine = create_engine(DB_URL)

def add_column_if_missing(table, column, col_type):
    with engine.connect() as conn:
        print(f"Checking {table}.{column}...")
        try:
            # Check if column exists using information_schema
            result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{column}'"))
            if result.fetchone():
                print(f"  Column {column} already exists in {table}.")
            else:
                print(f"  Column {column} missing. Adding...")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
                print(f"  Successfully added {column} to {table}.")
        except Exception as e:
            print(f"  Error checking/adding column: {e}")

if __name__ == "__main__":

    # Add new image_url column
    add_column_if_missing("articles", "image_url", "TEXT")
    
    print("Database schema check complete.")
