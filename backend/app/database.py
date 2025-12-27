from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .settings import settings
from sqlalchemy import text

engine = create_engine(
    settings.app_db_url,
    connect_args={"check_same_thread": False} if settings.app_db_url.startswith("sqlite") else {},
    # Optimization for 10,000+ concurrent requests
    pool_size=50 if not settings.app_db_url.startswith("sqlite") else 5,
    max_overflow=100 if not settings.app_db_url.startswith("sqlite") else 10,
    pool_timeout=30,
    pool_recycle=1800, # Recycle connections every 30 mins to avoid stale links
)

# Register JSON adapters for psycopg2 if using Postgres
if engine.url.drivername.startswith("postgresql"):
    try:
        import psycopg2.extras
        # Use the underlying DBAPI connection to register
        psycopg2.extras.register_default_json(conn_or_curs=None, globals=True)
        psycopg2.extras.register_default_jsonb(conn_or_curs=None, globals=True)
    except Exception:
        pass
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




