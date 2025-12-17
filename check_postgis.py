from sqlalchemy import create_engine, text
from backend.app.settings import settings

try:
    engine = create_engine(settings.app_db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name = 'postgis'"))
        row = result.fetchone()
        if row:
            print(f"FOUND: PostGIS version {row[1]} (Installed: {row[2]})")
        else:
            print("NOT FOUND: PostGIS extension is not listed in pg_available_extensions")
except Exception as e:
    print(f"ERROR: {e}")
