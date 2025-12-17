from sqlalchemy import create_engine, text
from backend.app.settings import settings

try:
    engine = create_engine(settings.app_db_url)
    with engine.connect() as conn:
        print("Connected. Checking top 10 extensions:")
        result = conn.execute(text("SELECT name FROM pg_available_extensions LIMIT 10"))
        for row in result:
            print(f"- {row[0]}")
except Exception as e:
    print(f"ERROR: {e}")
