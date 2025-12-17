from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .database import Base

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    domain: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # extracted
    disaster_type: Mapped[str] = mapped_column(String(32), index=True, default="unknown")
    province: Mapped[str] = mapped_column(String(64), index=True, default="unknown")
    event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    deaths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injured: Mapped[int | None] = mapped_column(Integer, nullable=True)
    damage_billion_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)

    agency: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True, index=True)
    event = relationship("Event", back_populates="articles")

    __table_args__ = (UniqueConstraint("domain", "url", name="uq_article_url"),)

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(256), unique=True, index=True)  # clustering key
    title: Mapped[str] = mapped_column(Text)
    disaster_type: Mapped[str] = mapped_column(String(32), index=True)
    province: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    deaths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injured: Mapped[int | None] = mapped_column(Integer, nullable=True)
    damage_billion_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)

    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1 based on multi-source agreement
    sources_count: Mapped[int] = mapped_column(Integer, default=1)

    articles = relationship("Article", back_populates="event")
