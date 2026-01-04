from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float, UniqueConstraint, JSON, Index, Boolean
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
    status: Mapped[str] = mapped_column(String(20), default="approved", index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Unique identifier for content to prevent re-crawling rejected news
    news_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    is_red_alert: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (
        UniqueConstraint("domain", "url", name="uq_article_url"),
        Index("ix_article_status_published", status, published_at),
        Index("ix_article_status_province_date", status, province, published_at),
        Index("ix_article_status_type_date", status, disaster_type, published_at),
        Index("ix_article_prov_type_date", province, disaster_type, published_at),
        Index("ix_article_event_status", event_id, status),
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
    is_red_alert: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    articles = relationship("Article", back_populates="event")

    __table_args__ = (
        Index("ix_event_type_date", disaster_type, started_at),
        Index("ix_event_province_date", province, started_at),
        Index("ix_event_prov_type_date", province, disaster_type, started_at),
    )

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", index=True) # "user", "admin"
    favorite_province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Blacklist(Base):
    """Stores hashes of articles that were rejected by admin to prevent re-crawling."""
    __tablename__ = "blacklist"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CrowdsourcedReport(Base):
    __tablename__ = "crowdsourced_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True, index=True)
    province: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Contact info for guest/user
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True) # "pending", "approved", "rejected"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User")
    event = relationship("Event")

class EventFollow(Base):
    __tablename__ = "event_follows"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_user_event_follow"),
    )

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True) # "new_article", "report_approved", etc.
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class CrawlerStatus(Base):
    __tablename__ = "crawler_status"
    source_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="success") # "success", "error", "warning"
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    articles_scanned: Mapped[int] = mapped_column(Integer, default=0)
    articles_added: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    feed_used: Mapped[str | None] = mapped_column(String(255), nullable=True) # e.g. "primary_rss", "gnews", "html_scraper"

class AiFeedback(Base):
    __tablename__ = "ai_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_type: Mapped[str] = mapped_column(String(32))
    corrected_type: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    article = relationship("Article")
    user = relationship("User")

class RescueHotline(Base):
    __tablename__ = "rescue_hotlines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    province: Mapped[str] = mapped_column(String(64), index=True)
    agency: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
