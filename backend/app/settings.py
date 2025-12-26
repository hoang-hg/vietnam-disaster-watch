from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import Field

# Build absolute path to data/app.db
# This file is in backend/app/settings.py -> parent.parent is backend/
BASE_DIR = Path(__file__).resolve().parent.parent
# Keep SQLite as fallback or simple default, but prefer Env Var
DB_PATH = BASE_DIR / "data" / "app.db"

class Settings(BaseSettings):
    # Default to SQLite if DATABASE_URL not set
    # Alias validation to read from APP_DB_URL or DATABASE_URL
    app_db_url: str = Field(
        default="sqlite:///" + str(DB_PATH), 
        validation_alias="APP_DB_URL"
    )
    
    # Allow overriding with PostgreSQL URL via env var
    # Example: postgresql://postgres:password@localhost:5432/viet_disaster_watch
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )
    
    crawl_interval_minutes: int = 60
    app_timezone: str = "Asia/Ho_Chi_Minh"
    user_agent: str = "Mozilla/5.0 (compatible; VietDisasterBot/1.0)"
    
    # Auth
    secret_key: str = Field(default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7", validation_alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7 # 7 days
    
    # List of rotate user agents
    user_agents: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    ]
    # SMTP Configuration
    smtp_host: str | None = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, validation_alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, validation_alias="SMTP_PASSWORD")
    smtp_tls: bool = Field(default=True, validation_alias="SMTP_TLS")

    # Reduce timeout so slow sources don't block a whole crawl cycle too long
    request_timeout_seconds: int = 15

settings = Settings()
