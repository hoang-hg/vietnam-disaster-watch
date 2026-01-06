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
    Ensures optimal caching for CDNs like Cloudflare and safe defaults.
    """
    response = await call_next(request)
    
    # Security: Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Add Vary header for compression and auth awareness
    response.headers["Vary"] = "Accept-Encoding, Authorization"
    
    # Ensure a default Cache-Control if not set
    if not response.headers.get("Cache-Control"):
        if request.url.path.startswith("/api"):
            # API responses should not be cached by default for security
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    return response

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for OPTIONS requests
    if request.method == "OPTIONS":
        return await call_next(request)

    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    # Handle multiple IPs in header (take the first one)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    now = time.time()
    
    # Whitelist for static/local
    if request.url.path.startswith("/static"):
        return await call_next(request)

    # Filter out old requests
    window_start = now - RATE_PERIOD
    request_counts[client_ip] = [t for t in request_counts[client_ip] if t > window_start]
    
    # Use the defined constant instead of hardcoded 100
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return Response(content="Too Many Requests", status_code=429)
    
    request_counts[client_ip].append(now)
    
    # Periodically clean up the dictionary to prevent memory growth
    if len(request_counts) > 1000:
        # Optimization: Clear expired timestamps for all IPs when map gets large
        cleanup_threshold = now - RATE_PERIOD
        for ip in list(request_counts.keys()):
            # Keep only valid timestamps
            valid_requests = [t for t in request_counts[ip] if t > cleanup_threshold]
            if valid_requests:
                request_counts[ip] = valid_requests
            else:
                del request_counts[ip]

    return await call_next(request)

# GLOBAL EXCEPTION HANDLER
from fastapi.responses import JSONResponse
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("uvicorn.error").error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Lỗi nội bộ server. Vui lòng thử lại sau.", "error_type": type(exc).__name__}
    )

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(user_router)

# Health check endpoint for Docker/monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy", "service": "viet-disaster-watch"}

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
    
    # 0.1 Capture Main Loop for Broadcast (Cross-thread SSE)
    import asyncio
    from . import broadcast, ws
    try:
        loop = asyncio.get_running_loop()
        broadcast.set_main_loop(loop)
        ws.manager.set_main_loop(loop)
    except RuntimeError:
        pass

    # 1. Initial full crawl on startup
    # Use scheduler to run in background thread to avoid blocking main loop (WebSocket handshake)
    import pytz
    from datetime import datetime, timedelta
    tz = pytz.timezone(settings.app_timezone)
    scheduler.add_job(
        process_once,
        'date',
        run_date=datetime.now(tz) + timedelta(seconds=15),
        id="startup_crawl"
    )

    # Tier 1: Critical Official Sources (High Frequency: 15 mins)
    # Includes National/Provincial KTTV, Earthquake Center, and Dyke Management
    from .sources import SOURCES
    tier1_sources = [s.name for s in SOURCES if any(kw in s.name for kw in [
        "KTTV Quốc gia", "KTTV Ninh Bình", "KTTV Thanh Hóa", "Cục PCTT (MARD)", "PCTT Hà Nội", 
        "Cục Kiểm lâm (PCCCR)", "Viện Vật lý Địa cầu", "KTTV An Giang", "KTTV Hưng Yên", 
        "KTTV Yên Bái", "Cục Quản lý đê điều", "VMRCC (Cứu nạn hàng hải)",
        "Tạp chí Khí tượng Thủy văn", "Ủy ban Sông Mê Công Việt Nam", "Báo Biên phòng"
    ])]

    # Tier 2: Major National News (Medium Frequency: 30 mins)
    tier2_sources = [
        "VnExpress", "Tuổi Trẻ", "Thanh Niên", "Dân Trí", "SGGP", "Lao Động", 
        "VietnamPlus", "Báo Tin tức", "CAND", "QĐND", "VTV News", "Pháp luật TP.HCM",
        "VietNamNet", "Nhân Dân", "Tiền Phong", "Người Lao Động", "Quân đội Nhân dân", "Báo Chính Phủ", 
        "Nông Nghiệp & Môi trường", "Báo Dân tộc và Phát triển","Báo Giao thông", "Cổng TTĐT Chính phủ (Công báo)",
        "Bnews", "Báo Nông nghiệp VN", "Tạp chí Giao thông", "Báo Công lý", "Báo Văn hóa", "Báo Xây dựng",
        "VnEconomy", "VTC News", "Báo Quốc tế", "Dân Việt", "VOV", "Báo Công Thương", "Vietnam.vn",
        "Báo Thanh tra", "Bộ Công an", "Giáo dục & Thời đại"
    ]

    # Job 1: Group 1 (Critical Official Sources) - Frequency: 15 MINUTES
    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=120, jitter=10),
        kwargs={"only_sources": tier1_sources},
        id="crawl_group1_critical",
        replace_existing=True,
        misfire_grace_time=300
    )

    # Job 2: Group 2 (Major National News) - Frequency: 30 MINUTES
    scheduler.add_job(
        process_once,
        trigger=IntervalTrigger(minutes=240, jitter=20),
        kwargs={"only_sources": tier2_sources},
        id="crawl_group2_major",
        replace_existing=True,
        misfire_grace_time=600
    )

    # Job 3: Group 3 (Full Sweep / Province Papers) - Frequency: 60 MINUTES
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



