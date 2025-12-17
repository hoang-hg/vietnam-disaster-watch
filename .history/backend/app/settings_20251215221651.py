from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_db_url: str = "sqlite:///./data/app.db"
    crawl_interval_minutes: int = 15
    app_timezone: str = "Asia/Ho_Chi_Minh"
    user_agent: str = "VietDisasterWatchBot/1.0 (+contact: you@example.com)"
    # Reduce timeout so slow sources don't block a whole crawl cycle too long
    request_timeout_seconds: int = 10

    class Config:
        env_prefix = ""
        case_sensitive = False

settings = Settings()
