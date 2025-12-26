from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .database import Base, engine

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    domain: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # extracted details matching the user's report format
    disaster_type: Mapped[str] = mapped_column(String(32), index=True, default="unknown")
    province: Mapped[str] = mapped_column(String(64), index=True, default="unknown")
    commune: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    village: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    route: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    characteristics: Mapped[str | None] = mapped_column(Text, nullable=True)

    stage: Mapped[str] = mapped_column(String(32), index=True, default="INCIDENT")
    event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    deaths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injured: Mapped[int | None] = mapped_column(Integer, nullable=True)
    damage_billion_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)

    agency: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_broken: Mapped[int] = mapped_column(Integer, default=0) # 0=no, 1=yes/broken
    impact_details: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True, index=True)
    event = relationship("Event", back_populates="articles")

    needs_verification: Mapped[bool] = mapped_column(Integer, default=0) # 0=no, 1=yes
    
    # 3-Tier filtering status
    # 'approved': automatically accepted or admin approved
    # 'pending': waiting for admin review (score in grey area)
    # 'rejected': admin explicitly rejected
    status: Mapped[str] = mapped_column(String(20), default="approved", index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Unique identifier for content to prevent re-crawling rejected news
    news_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    __table_args__ = (
        UniqueConstraint("domain", "url", name="uq_article_url"),
    )

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(256), unique=True, index=True)  # clustering key
    title: Mapped[str] = mapped_column(Text, index=True)
    disaster_type: Mapped[str] = mapped_column(String(32), index=True)
    province: Mapped[str] = mapped_column(String(64), index=True)
    commune: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    village: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    route: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    characteristics: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage: Mapped[str] = mapped_column(String(32), index=True, default="INCIDENT")
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    deaths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injured: Mapped[int | None] = mapped_column(Integer, nullable=True)
    damage_billion_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1 based on multi-source agreement
    sources_count: Mapped[int] = mapped_column(Integer, default=1)
    needs_verification: Mapped[bool] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    articles = relationship("Article", back_populates="event")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", index=True) # "user", "admin"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Blacklist(Base):
    """Stores hashes of articles that were rejected by admin to prevent re-crawling."""
    __tablename__ = "blacklist"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

