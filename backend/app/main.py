from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.websockets import WebSocket
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime, timedelta
import pytz

# Third-party Imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# App Imports
from .settings import settings
from .api import router as api_router
from .auth_router import router as auth_router
from .user_router import router as user_router
from .crawler import process_once, cleanup_old_pending_articles
from .source_monitor import monitor_now
from .log_utils import rotate_logs
from . import models, database, auth, broadcast, ws, sources

# --- SCHEDULER SETUP (Global) ---
job_defaults = {
    'coalesce': True,
    'max_instances': 2,
    'misfire_grace_time': 300
}
scheduler = BackgroundScheduler(timezone=settings.app_timezone, job_defaults=job_defaults)

# --- RATE LIMITER SETUP ---
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. Database Initialization
    database.Base.metadata.create_all(bind=database.engine)
    
    # 0.1 Seed Fixed Admin Accounts
    db = None
    try:
        db = next(auth.get_db())
        default_admin_pw = getattr(settings, "default_admin_password", "admin123")
        fixed_admins = [
            ("admin@vdw.com", default_admin_pw),
            ("quantri@vdw.com", default_admin_pw),
            ("root@vdw.com", default_admin_pw)
        ]
        created_count = 0
        for email, pw in fixed_admins:
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                hashed = auth.get_password_hash(pw)
                new_admin = models.User(
                    email=email,
                    hashed_password=hashed,
                    full_name="Administrator",
                    role="admin",
                    favorite_province=None
                )
                db.add(new_admin)
                created_count += 1
        if created_count > 0:
            db.commit()
            logger.info(f"[SEED] Created {created_count} Admin accounts.")
    except Exception as e:
        logger.error(f"[SEED] Failed to seed admins: {e}")
    finally:
        if db: db.close()

    # 0.2 Capture Main Loop for Broadcast
    try:
        loop = asyncio.get_running_loop()
        broadcast.set_main_loop(loop)
        ws.manager.set_main_loop(loop)
    except RuntimeError:
        pass

    # 1. Scheduler Configuration
    # Tier 1 Sources (Critical)
    tier1_kws = [
        "KTTV Quốc gia", "KTTV Ninh Bình", "KTTV Thanh Hóa", "Cục PCTT (MARD)", "PCTT Hà Nội", 
        "Cục Kiểm lâm (PCCCR)", "Viện Vật lý Địa cầu", "KTTV An Giang", "KTTV Hưng Yên", 
        "KTTV Yên Bái", "Cục Quản lý đê điều", "VMRCC (Cứu nạn hàng hải)",
        "Tạp chí Khí tượng Thủy văn", "Ủy ban Sông Mê Công Việt Nam", "Báo Biên phòng"
    ]
    tier1_sources = [s.name for s in sources.SOURCES if any(kw in s.name for kw in tier1_kws)]

    # Tier 2 Sources (Major News)
    tier2_sources = [
        "VnExpress", "Tuổi Trẻ", "Thanh Niên", "Dân Trí", "SGGP", "Lao Động", 
        "VietnamPlus", "Báo Tin tức", "CAND", "QĐND", "VTV News", "Pháp luật TP.HCM",
        "VietNamNet", "Nhân Dân", "Tiền Phong", "Người Lao Động", "Quân đội Nhân dân", "Báo Chính Phủ", 
        "Nông Nghiệp & Môi trường", "Báo Dân tộc và Phát triển","Báo Giao thông", "Cổng TTĐT Chính phủ (Công báo)",
        "Bnews", "Báo Nông nghiệp VN", "Tạp chí Giao thông", "Báo Công lý", "Báo Văn hóa", "Báo Xây dựng",
        "VnEconomy", "VTC News", "Báo Quốc tế", "Dân Việt", "VOV", "Báo Công Thương", "Vietnam.vn",
        "Báo Thanh tra", "Bộ Công an", "Giáo dục & Thời đại"
    ]

    # Startup Crawl (15s delay)
    tz = pytz.timezone(settings.app_timezone)
    scheduler.add_job(
        process_once,
        'date',
        run_date=datetime.now(tz) + timedelta(seconds=15),
        id="startup_crawl",
        replace_existing=True
    )

    # Recurring Jobs
    scheduler.add_job(process_once, trigger=IntervalTrigger(minutes=90, jitter=60), kwargs={"only_sources": tier1_sources}, id="crawl_group1_critical", replace_existing=True)
    scheduler.add_job(process_once, trigger=IntervalTrigger(minutes=180, jitter=120), kwargs={"only_sources": tier2_sources}, id="crawl_group2_major", replace_existing=True)
    scheduler.add_job(process_once, trigger=IntervalTrigger(minutes=360, jitter=300), id="crawl_group3_full", replace_existing=True)
    scheduler.add_job(lambda: asyncio.run(monitor_now()), trigger=IntervalTrigger(minutes=720, jitter=60), id="source_health_monitor", replace_existing=True)
    scheduler.add_job(rotate_logs, trigger=IntervalTrigger(hours=12, jitter=60), id="log_rotation", replace_existing=True)
    scheduler.add_job(cleanup_old_pending_articles, trigger=IntervalTrigger(hours=24, jitter=120), id="db_cleanup_pending", replace_existing=True)

    scheduler.start()

    yield
    
    # Shutdown
    scheduler.shutdown(wait=False)

app = FastAPI(
    title="Viet Disaster Watch API",
    version="0.1.0",
    description="API tổng hợp tin thiên tai từ báo (RSS/GNews RSS), phân loại & nhóm sự kiện.",
    lifespan=lifespan
)

# Apply Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def cdn_optimization_middleware(request: Request, call_next):
    """Ensures optimal caching for CDNs like Cloudflare and safe defaults."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Vary"] = "Accept-Encoding, Authorization"
    if not response.headers.get("Cache-Control"):
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    return response

# Routes
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "viet-disaster-watch"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await ws.manager.connect(websocket)
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws.manager.disconnect(websocket)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger("uvicorn.error").error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Lỗi nội bộ server. Vui lòng thử lại sau.", "error_type": type(exc).__name__}
    )

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(user_router)




