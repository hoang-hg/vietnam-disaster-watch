from datetime import datetime
from pydantic import BaseModel

class ArticleOut(BaseModel):
    id: int
    source: str
    domain: str
    title: str
    url: str
    published_at: datetime
    disaster_type: str
    province: str
    deaths: int | None
    missing: int | None
    injured: int | None
    damage_billion_vnd: float | None
    agency: str | None
    summary: str | None
    full_text: str | None
    image_url: str | None
    event_id: int | None

    class Config:
        from_attributes = True

class EventOut(BaseModel):
    id: int
    key: str
    title: str
    disaster_type: str
    province: str
    started_at: datetime
    last_updated_at: datetime
    deaths: int | None
    missing: int | None
    injured: int | None
    damage_billion_vnd: float | None
    lat: float | None
    lon: float | None
    details: dict | None
    risk_level: int | None
    confidence: float
    sources_count: int
    image_url: str | None = None
    source: str | None = None

    class Config:
        from_attributes = True

class EventDetailOut(EventOut):
    articles: list[ArticleOut]
