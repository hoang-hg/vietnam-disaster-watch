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
    commune: str | None = None
    village: str | None = None
    route: str | None = None
    cause: str | None = None
    characteristics: str | None = None
    deaths: int | None
    missing: int | None
    injured: int | None
    damage_billion_vnd: float | None
    agency: str | None
    summary: str | None
    full_text: str | None
    is_broken: int = 0
    image_url: str | None
    event_id: int | None
    needs_verification: int = 0
    status: str | None = None
    score: float | None = None

    class Config:
        from_attributes = True

class EventOut(BaseModel):
    id: int
    key: str
    title: str
    disaster_type: str
    province: str
    commune: str | None = None
    village: str | None = None
    route: str | None = None
    cause: str | None = None
    characteristics: str | None = None
    started_at: datetime
    last_updated_at: datetime
    deaths: int | None
    missing: int | None
    injured: int | None
    damage_billion_vnd: float | None
    lat: float | None
    lon: float | None
    details: dict | None

    confidence: float
    sources_count: int
    articles_count: int = 0
    needs_verification: int = 0
    image_url: str | None = None
    source: str | None = None

    class Config:
        from_attributes = True

class EventDetailOut(EventOut):
    articles: list[ArticleOut]

class EventUpdate(BaseModel):
    title: str | None = None
    disaster_type: str | None = None
    province: str | None = None
    commune: str | None = None
    village: str | None = None
    route: str | None = None
    cause: str | None = None
    characteristics: str | None = None
    deaths: int | None = None
    missing: int | None = None
    injured: int | None = None
    damage_billion_vnd: float | None = None
    needs_verification: int | None = None
