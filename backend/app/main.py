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

# Configure scheduler to handle slow jobs strictly
# max_instances=2 allows overlap if one is stuck, but mostly fixes the warning.
# coalesce=True rolls up missed executions into one.
job_defaults = {
    'coalesce': True,
    'max_instances': 2,
    'misfire_grace_time': 300
}
scheduler = BackgroundScheduler(timezone=settings.app_timezone, job_defaults=job_defaults)

@app.on_event("startup")
async def on_startup():
    # 1. Initial full crawl on startup
    import asyncio
    asyncio.create_task(_process_once_async())

    # Tier 1: Critical Official Sources (High Frequency: 15 mins)
    # Includes National/Provincial KTTV, Earthquake Center, and Dyke Management
    def get_tier1_sources():
        from .sources import load_sources_from_json
        from pathlib import Path
        # sources.json is in backend root (parent of app package)
        root_dir = Path(__file__).resolve().parent.parent
        srcs = load_sources_from_json(str(root_dir / "sources.json"))
        return [s.name for s in srcs if any(kw in s.name for kw in ["KTTV", "Viện Vật lý", "Đê điều", "PCTT", "Cứu nạn"])]

    # Tier 2: Major National News (Medium Frequency: 30 mins)
    # These sources have high coverage and fast reporting but are not official disaster agencies.
    def get_tier2_sources():
        return [
            "VnExpress", "Tuổi Trẻ", "Thanh Niên", "Dân Trí", "SGGP", "Lao Động", 
            "VietnamPlus (TTXVN)", "Báo Tin tức (TTXVN)", "CAND", "QĐND", "VTV News", "Pháp luật TP.HCM"
        ]

    # Tier 1: 15 mins
    scheduler.add_job(
        lambda: process_once(only_sources=get_tier1_sources()),
        trigger=IntervalTrigger(minutes=15),
        id="crawl_tier1_official",
        replace_existing=True,
    )

    # Tier 2: 30 mins
    scheduler.add_job(
        lambda: process_once(only_sources=get_tier2_sources()),
        trigger=IntervalTrigger(minutes=30),
        id="crawl_tier2_major",
        replace_existing=True,
    )

    # Tier 3: 60 mins (Full Sweep including 63 Province Papers)
    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=60),
        id="crawl_tier3_full",
        replace_existing=True,
    )

    scheduler.start()

@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)
