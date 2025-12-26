from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .settings import settings
from .api import router as api_router
from .auth_router import router as auth_router
from .crawler import process_once, _process_once_async

app = FastAPI(
    title="Viet Disaster Watch API",
    version="0.1.0",
    description="API tổng hợp tin thiên tai từ 12 báo (RSS/GNews RSS), phân loại & nhóm sự kiện.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)

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
    # 0. Create database tables if they don't exist
    from .database import engine, Base
    from . import models # ensure models are registered
    Base.metadata.create_all(bind=engine)

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
        return [s.name for s in srcs if any(kw in s.name for kw in ["KTTV Quốc gia", "KTTV Ninh Bình", 
        "KTTV Thanh Hóa", "Cục PCTT (MARD)", "PCTT Hà Nội", "Cục Kiểm lâm (PCCCR)", "Viện Vật lý Địa cầu", 
        "KTTV An Giang", "KTTV Hưng Yên", "KTTV Yên Bái", "Cục Quản lý đê điều", "VMRCC (Cứu nạn hàng hải)",
        "Tạp chí Khí tượng Thủy văn", "Ủy ban Sông Mê Công Việt Nam", "Báo Biên phòng"])]

    # Tier 2: Major National News (Medium Frequency: 30 mins)
    # These sources have high coverage and fast reporting but are not official disaster agencies.
    def get_tier2_sources():
        return [
            "VnExpress", "Tuổi Trẻ", "Thanh Niên", "Dân Trí", "SGGP", "Lao Động", 
            "VietnamPlus", "Báo Tin tức", "CAND", "QĐND", "VTV News", "Pháp luật TP.HCM",
            "VietNamNet", "Nhân Dân", "Tiền Phong", "Người Lao Động", "Quân đội Nhân dân", "Báo Chính Phủ", 
            "Nông Nghiệp & Môi trường", "Báo Dân tộc và Phát triển","Báo Giao thông", "Cổng TTĐT Chính phủ (Công báo)",
            "Bnews", "Báo Nông nghiệp VN", "Tạp chí Giao thông", "Báo Công lý", "Báo Văn hóa", "Báo Xây dựng",
            "VnEconomy", "VTC News", "Báo Quốc tế", "Dân Việt", "VOV", "Báo Công Thương", "Vietnam.vn",
            "Báo Thanh tra", "Bộ Công an", "Giáo dục & Thời đại"
        ]

    # Job 1: Group 1 (Critical Official Sources) - Frequency: 15 mins
    # Includes National/Provincial KTTV, Earthquake Center, and Dyke Management
    scheduler.add_job(
        lambda: process_once(only_sources=get_tier1_sources()),
        trigger=IntervalTrigger(minutes=15, jitter=5),
        id="crawl_group1_critical",
        replace_existing=True,
        misfire_grace_time=60
    )

    # Job 2: Group 2 (Major National News) - Frequency: 60 mins
    # Coverage: VnExpress, Tuổi Trẻ, Thanh Niên, Dân Trí, VTV, VOV...
    scheduler.add_job(
        lambda: process_once(only_sources=get_tier2_sources()),
        trigger=IntervalTrigger(minutes=60, jitter=15),
        id="crawl_group2_major",
        replace_existing=True,
        misfire_grace_time=180
    )

    # Job 3: Group 3 (Full Sweep / Province Papers) - Frequency: 6 HOURS (360 mins)
    # Performs a complete scan of all sources in sources.json.
    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=360, jitter=120),
        id="crawl_group3_full",
        replace_existing=True,
        misfire_grace_time=300
    )

    # Job 4: Source Health Monitor (Periodic Check) - Frequency: 12 HOURS (720 mins)
    # Checks for broken RSS feeds and inactive sources.
    from .source_monitor import monitor_now
    scheduler.add_job(
        lambda: asyncio.run(monitor_now()),
        trigger=IntervalTrigger(minutes=720, jitter=60),
        id="source_health_monitor",
        replace_existing=True,
        misfire_grace_time=300
    )

    # Job 5: Potential Disaster Recovery (Auto-Ingest) - DISABLED
    # This was replaced by the manual 3-tier review dashboard.
    # The JSONL logs are now only for audit/audit trail.


    # Job 6: Log Rotation & Cleanup - Frequency: 12 HOURS
    # Keeps log files small and prevents disk full issues.
    from .log_utils import rotate_logs
    scheduler.add_job(
        rotate_logs,
        trigger=IntervalTrigger(hours=12, jitter=60),
        id="log_rotation",
        replace_existing=True,
        misfire_grace_time=600
    )

    scheduler.start()

@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)
