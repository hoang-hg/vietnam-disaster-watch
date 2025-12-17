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




