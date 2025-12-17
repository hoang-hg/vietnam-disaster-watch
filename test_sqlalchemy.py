from sqlalchemy import create_engine, text
from backend.app.settings import settings

print(f"Testing SQLAlchemy with URL: {settings.app_db_url}")

try:
    engine = create_engine(settings.app_db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        logging.info(f"Success! Tables: {result.fetchall()}")
except Exception as e:
    print(f"Failed: {e}")
