from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .settings import settings
from .api import router as api_router
from .crawler import process_once, _process_once_async

app = FastAPI(
    title="Viet Disaster Watch API",
    version="0.1.0",
    description="API tổng hợp tin thiên tai từ 12 báo (RSS/GNews RSS), phân loại & nhóm sự kiện.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

scheduler = BackgroundScheduler(timezone=settings.app_timezone)

@app.on_event("startup")
async def on_startup():
    try:
        await _process_once_async()
    except Exception as e:
        print(f"[WARN] initial crawl failed: {e}")

    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=settings.crawl_interval_minutes),
        id="crawl_job",
        replace_existing=True,
    )
    scheduler.start()

@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)
