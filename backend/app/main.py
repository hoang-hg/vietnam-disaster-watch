from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .settings import settings
from .api import router as api_router
from .auth_router import router as auth_router
from .user_router import router as user_router
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

# Custom Rate Limiter Middleware (Simple Memory-based)
from fastapi import Request, Response
import time
from collections import defaultdict

request_counts = defaultdict(list)
RATE_LIMIT = 50  # requests
RATE_PERIOD = 60 # seconds

@app.middleware("http")
async def cdn_optimization_middleware(request: Request, call_next):
    """
    Ensures optimal caching for CDNs like Cloudflare.
    """
    response = await call_next(request)
    # Add Vary header for compression awareness
    response.headers["Vary"] = "Accept-Encoding, Authorization"
    # Ensure a default Cache-Control if not set (to prevent CDN from caching sensitive data)
    if not response.headers.get("Cache-Control"):
        if request.url.path.startswith("/api"):
            # Default private for API if not specified
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    client_ip = request.client.host
    now = time.time()
    
    # Simple whitelist for static or local requests if needed
    if request.url.path.startswith("/static"):
        return await call_next(request)

    # Filter out old requests
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < RATE_PERIOD]
    
    # Increase limit to 100 for smoother admin/dev experience
    limit = 100 
    
    if len(request_counts[client_ip]) >= limit:
        return Response(content="Too Many Requests", status_code=429)
    
    request_counts[client_ip].append(now)
    response = await call_next(request)
    return response

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(user_router)

from .ws import manager
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        while True:
            # Keep connection alive, we don't expect client messages for now
            await websocket.receive_text()
    except Exception as e:
        # Client disconnected or other error
        pass
    finally:
        manager.disconnect(websocket)

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
    # 1. Initial full crawl on startup
    # Use scheduler to run in background thread to avoid blocking main loop (WebSocket handshake)
    from datetime import datetime, timedelta
    scheduler.add_job(
        process_once,
        'date',
        run_date=datetime.now() + timedelta(seconds=15),
        id="startup_crawl"
    )

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

    # Job 1: Group 1 (Critical Official Sources) - Frequency: 2 HOURS (120 mins)
    # Includes National/Provincial KTTV, Earthquake Center, and Dyke Management
    scheduler.add_job(
        lambda: process_once(only_sources=get_tier1_sources()),
        trigger=IntervalTrigger(minutes=120, jitter=10),
        id="crawl_group1_critical",
        replace_existing=True,
        misfire_grace_time=300
    )

    # Job 2: Group 2 (Major National News) - Frequency: 4 HOURS (240 mins)
    # Coverage: VnExpress, Tuổi Trẻ, Thanh Niên, Dân Trí, VTV, VOV...
    scheduler.add_job(
        lambda: process_once(only_sources=get_tier2_sources()),
        trigger=IntervalTrigger(minutes=240, jitter=20),
        id="crawl_group2_major",
        replace_existing=True,
        misfire_grace_time=600
    )

    # Job 3: Group 3 (Full Sweep / Province Papers) - Frequency: 8 HOURS (480 mins)
    # Performs a complete scan of all sources in sources.json.
    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=480, jitter=120),
        id="crawl_group3_full",
        replace_existing=True,
        misfire_grace_time=1200
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

    # Job 7: Database Maintenance - Frequency: 24 HOURS
    # Automatically deletes pending articles older than 30 days.
    from .crawler import cleanup_old_pending_articles
    scheduler.add_job(
        cleanup_old_pending_articles,
        trigger=IntervalTrigger(hours=24, jitter=120),
        id="db_cleanup_pending",
        replace_existing=True,
        misfire_grace_time=3600
    )

    scheduler.start()

@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)
