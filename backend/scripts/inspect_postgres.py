from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()

# Force using the Postgres URL from .env
db_url = os.getenv("APP_DB_URL")
if not db_url or "sqlite" in db_url:
    print("Error: APP_DB_URL is not set to Postgres.")
    # Fallback to hardcoded for diagnosis if env fails reading
    db_url = "postgresql://postgres:12102004@localhost:5432/viet_disaster_watch"

print(f"Connecting to: {db_url}")
engine = create_engine(db_url)
inspector = inspect(engine)

print("--- Articles Columns ---")
columns = [c['name'] for c in inspector.get_columns('articles')]
print(sorted(columns))

print("\n--- Events Columns ---")
columns_events = [c['name'] for c in inspector.get_columns('events')]
print(sorted(columns_events))
