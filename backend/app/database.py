from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .settings import settings
from sqlalchemy import text

engine = create_engine(
    settings.app_db_url,
    connect_args={"check_same_thread": False} if settings.app_db_url.startswith("sqlite") else {},
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Runtime lightweight migration: add `canonical_url` column if missing (for sqlite)
def _ensure_canonical_column():
    try:
        if not settings.app_db_url.startswith("sqlite"):
            return
        with engine.connect() as conn:
            # Check if articles table exists
            r = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'"))
            if r.fetchone() is None:
                return
            cols = conn.execute(text("PRAGMA table_info('articles')")).fetchall()
            col_names = [c[1] for c in cols]
            if 'canonical_url' not in col_names:
                print('[MIGRATE] adding canonical_url column to articles')
                conn.execute(text("ALTER TABLE articles ADD COLUMN canonical_url TEXT"))
    except Exception as e:
        print(f"[MIGRATE] failed to ensure canonical_url: {e}")


# Run migration at import time
_ensure_canonical_column()
