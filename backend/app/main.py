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
    # Run initial crawl in background so we don't block startup
    import asyncio
    asyncio.create_task(_process_once_async())

    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=settings.crawl_interval_minutes),
        id="crawl_job_general",
        replace_existing=True,
    )
    
    # 2. KTTV Special Schedule (Fast Update: 2 minutes)
    # We use a lambda or wrapper to pass arguments if needed, 
    # but apscheduler supports args/kwargs.
    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=10),
        id="crawl_job_kttv",
        kwargs={"only_sources": ["KTTV Quốc gia"]}, # Prioritize KTTV 
        replace_existing=True,
    )
    scheduler.start()

@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)
