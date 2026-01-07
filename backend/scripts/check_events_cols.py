from sqlalchemy import create_engine, text
import os

db_url = "postgresql://postgres:12102004@localhost:5432/viet_disaster_watch"
engine = create_engine(db_url)

target_cols = ['landmark', 'location_description', 'lat', 'lon', 'details', 'needs_verification', 'image_url', 'stage']

print(f"Checking columns in 'events' table for DB: {db_url}")

with engine.connect() as conn:
    # Check alembic version
    res = conn.execute(text("SELECT * FROM alembic_version")).fetchall()
    print(f"Current Alembic Version: {res}")

    # Check columns
    existing_cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='events'")).fetchall()
    existing_cols = [r[0] for r in existing_cols]
    
    print("\n--- Existing Columns in Events ---")
    for col in sorted(existing_cols):
        print(f" - {col}")
        
    print("\n--- Verification ---")
    for col in target_cols:
        exists = col in existing_cols
        print(f"Column '{col}': {'EXISTS' if exists else 'MISSING'}")
