from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
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
    location_description: str | None = None
    deaths: int | None = 0
    missing: int | None = 0
    injured: int | None = 0
    damage_billion_vnd: float | None = 0.0
    agency: str | None = None
    summary: str | None = None
    # full_text removed to prevent heavy payloads and N+1 queries in defer() scenarios
    is_broken: bool = False
    image_url: str | None = None
    event_id: int | None = None
    needs_verification: bool = False
    status: str | None = None
    score: float | None = None

class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    key: str
    title: str
    disaster_type: str
    province: str
    commune: str | None = None
    village: str | None = None
    route: str | None = None
    location_description: str | None = None
    cause: str | None = None
    characteristics: str | None = None
    started_at: datetime
    last_updated_at: datetime
    deaths: int | None = 0
    missing: int | None = 0
    injured: int | None = 0
    damage_billion_vnd: float | None = 0.0
    lat: float | None = None
    lon: float | None = None
    details: dict | None = None

    confidence: float
    sources_count: int
    articles_count: int = 0
    needs_verification: bool = False
    image_url: str | None = None
    source: str | None = None
    source_url: str | None = None

class EventDetailOut(EventOut):
    articles: list[ArticleOut]

class EventUpdate(BaseModel):
    title: str | None = None
    disaster_type: str | None = None
    province: str | None = None
    commune: str | None = None
    village: str | None = None
    route: str | None = None
    location_description: str | None = None
    cause: str | None = None
    characteristics: str | None = None
    deaths: int | None = None
    missing: int | None = None
    injured: int | None = None
    damage_billion_vnd: float | None = None
    needs_verification: bool | None = None

class CrowdsourcedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int | None = None
    event_id: int | None = None
    province: str | None = None
    lat: float | None = None
    lon: float | None = None
    description: str
    image_url: str | None = None
    
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    
    status: str
    created_at: datetime

class CrowdsourcedReportCreate(BaseModel):
    event_id: int | None = None
    province: str | None = None
    lat: float | None = None
    lon: float | None = None
    description: str
    image_url: str | None = None
    
    name: str = "Khách" # Default for guests
    phone: str | None = None
    address: str | None = None

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    type: str
    title: str
    message: str
    link: str | None = None
    is_read: bool
    created_at: datetime

class RescueHotlineBase(BaseModel):
    province: str
    agency: str
    phone: str
    address: str | None = None

class RescueHotlineCreate(RescueHotlineBase):
    pass

class RescueHotlineUpdate(BaseModel):
    province: str | None = None
    agency: str | None = None
    phone: str | None = None
    address: str | None = None

class RescueHotlineOut(RescueHotlineBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    updated_at: datetime
