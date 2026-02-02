from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import get_db
from .log_utils import log_audit
from . import models, schemas, auth
from datetime import datetime, timezone, timedelta
from typing import List
from .api import get_date_range

from .limiter import limiter

router = APIRouter(prefix="/api/user", tags=["user"])

# Crowdsourcing
@router.post("/crowdsource/submit", response_model=schemas.CrowdsourcedReportOut)
@limiter.limit("5/minute")
def submit_report(
    request: Request, # Rate limiter needs request object in arguments
    report: schemas.CrowdsourcedReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(auth.get_current_user_optional)
):
    # [FIX] Double-submission check (same user/phone + same description + last 5 mins)
    recent_check = db.query(models.CrowdsourcedReport).filter(
        (models.CrowdsourcedReport.phone == report.phone) | (models.CrowdsourcedReport.user_id == (current_user.id if current_user else -1)),
        models.CrowdsourcedReport.description == report.description,
        models.CrowdsourcedReport.created_at > datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    ).first()
    
    if recent_check:
        return recent_check # Silently return the existing one to avoid error noise

    db_report = models.CrowdsourcedReport(
        user_id=current_user.id if current_user else None,
        **report.model_dump()
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Invalidate crowdsource caches
    from .cache import cache
    cache.delete_match("map_*")
    
    return db_report

@router.get("/crowdsource/approved", response_model=List[schemas.CrowdsourcedReportOut])
def get_approved_reports(
    min_lat: float | None = Query(None),
    max_lat: float | None = Query(None),
    min_lon: float | None = Query(None),
    max_lon: float | None = Query(None),
    db: Session = Depends(get_db)
):
    from .cache import cache
    cache_key = f"crowd_apprv_v1_{min_lat}_{max_lat}_{min_lon}_{max_lon}"
    cached = cache.get(cache_key)
    if cached: return cached

    # Optimized query: filter first, then limit if necessary
    query = db.query(models.CrowdsourcedReport).filter(
        models.CrowdsourcedReport.status == "approved"
    )
    
    if min_lat is not None: query = query.filter(models.CrowdsourcedReport.lat >= min_lat)
    if max_lat is not None: query = query.filter(models.CrowdsourcedReport.lat <= max_lat)
    if min_lon is not None: query = query.filter(models.CrowdsourcedReport.lon >= min_lon)
    if max_lon is not None: query = query.filter(models.CrowdsourcedReport.lon <= max_lon)

    res = query.order_by(models.CrowdsourcedReport.created_at.desc()).limit(200).all()
    # Cache results (including Pydantic serialization if necessary, but FastAPI handles models)
    cache.set(cache_key, res, ttl=60)
    return res

# Event Following
@router.post("/events/{event_id}/follow")
def toggle_follow_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Check existence of event first to fail fast
    # Use scalar query for event existence to be lighter
    event_exists = db.query(models.Event.id).filter(models.Event.id == event_id).first()
    if not event_exists:
        raise HTTPException(status_code=404, detail="Event not found")
        
    follow = db.query(models.EventFollow).filter(
        models.EventFollow.user_id == current_user.id,
        models.EventFollow.event_id == event_id
    ).first()
    
    if follow:
        db.delete(follow)
        db.commit()
        return {"status": "unfollowed"}
    else:
        db_follow = models.EventFollow(user_id=current_user.id, event_id=event_id)
        db.add(db_follow)
        db.commit()
        return {"status": "followed"}

@router.get("/events/followed", response_model=List[schemas.EventOut])
def get_followed_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Optimized: Join Follow -> Event directly instead of N+1 query pattern (Fetch IDs -> Filter IN)
    events = db.query(models.Event).join(
        models.EventFollow, models.EventFollow.event_id == models.Event.id
    ).filter(
        models.EventFollow.user_id == current_user.id
    ).all()
    
    return events

@router.get("/events/{event_id}/is-following")
def check_is_following(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Scalar query exists check is faster than fetching object
    is_following = db.query(models.EventFollow.id).filter(
        models.EventFollow.user_id == current_user.id,
        models.EventFollow.event_id == event_id
    ).first() is not None
    
    return {"is_following": is_following}

# Notifications
@router.get("/notifications", response_model=List[schemas.NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(50).all()

from fastapi.responses import JSONResponse

@router.get("/notifications/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    count = db.query(func.count(models.Notification.id)).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).scalar()
    # Explicitly set charset=utf-8 to satisfy strict linters/browsers
    return JSONResponse(content={"count": count or 0}, media_type="application/json; charset=utf-8")

@router.patch("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Use update() for atomic operation instead of fetch-modify-save
    rows = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == current_user.id
    ).update({"is_read": True})
    
    if rows == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.commit()
    return {"ok": True}

@router.patch("/notifications/read-all")
def mark_all_notifications_read(
	db: Session = Depends(get_db),
	current_user: models.User = Depends(auth.get_current_user)
):
	db.query(models.Notification).filter(
		models.Notification.user_id == current_user.id,
		models.Notification.is_read == False
	).update({"is_read": True})
	db.commit()
	return {"ok": True}

# Admin Endpoints for Crowdsourcing
@router.get("/admin/crowdsource/pending", response_model=List[schemas.CrowdsourcedReportOut])
def get_pending_reports(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    query = db.query(models.CrowdsourcedReport).filter(
        models.CrowdsourcedReport.status == "pending"
    )
    if start_date or end_date:
        d_start, d_end = get_date_range(0, None, start_date, end_date)
        query = query.filter(models.CrowdsourcedReport.created_at >= d_start, models.CrowdsourcedReport.created_at < d_end)
        
    return query.order_by(models.CrowdsourcedReport.created_at.asc()).all()

@router.patch("/admin/crowdsource/{report_id}/approve")
def approve_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    report = db.query(models.CrowdsourcedReport).filter(models.CrowdsourcedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.status = "approved"
    
    # Notify user if registered
    if report.user_id:
        notif = models.Notification(
            user_id=report.user_id,
            type="report_approved",
            title="Đóng góp đã được duyệt",
            message=f"Thông tin tại {report.province or 'hiện trường'} của bạn đã được Admin duyệt và hiển thị trên bản đồ.",
            link="/map",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(notif)
        
    # [FEATURE] Auto-convert approved report to an Event
    if not report.event_id:
        # Generate a unique key
        event_key = f"community_{report.id}_{int(report.created_at.timestamp())}"
        
        # Determine title
        evt_title = f"Tin báo cộng đồng: {report.description[:60]}"
        if len(report.description) > 60:
            evt_title += "..."
            
        new_event = models.Event(
            key=event_key,
            title=evt_title,
            disaster_type="community",
            province=report.province or "Toàn quốc",
            started_at=report.created_at.replace(tzinfo=None) if report.created_at and report.created_at.tzinfo else report.created_at,
            last_updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            lat=report.lat,
            lon=report.lon,
            confidence=1.0, # Admin approved
            sources_count=1,
            needs_verification=False,
            image_url=report.image_url,
            details={
                "source": "community", 
                "reporter_name": report.name, # Corrected mapping from model.name
                "full_description": report.description
            }
        )
        db.add(new_event)
        db.flush() # Generate ID
        report.event_id = new_event.id

        # [NEW] Create a "shadow article" so the event has content in the list
        report_art = models.Article(
            source="Cộng đồng",
            domain="community",
            title=evt_title,
            url="/rescue", # Link to rescue/community section
            published_at=report.created_at.replace(tzinfo=None) if report.created_at and report.created_at.tzinfo else report.created_at,
            disaster_type="community",
            province=report.province or "Toàn quốc",
            summary=report.description,
            event_id=new_event.id,
            status="approved",
            image_url=report.image_url
        )
        db.add(report_art)
        
    db.commit()
    
    log_audit("approve_report", admin.id, admin.email, details={"report_id": report_id, "description": report.description})
    
    # [OPTIMIZATION] Real-time broadcast for Community Event
    # Must run AFTER commit so background threads can see the data
    try:
        from .event_matcher import emit_event_notifications
        if report.event_id:
            emit_event_notifications(db, report.event_id, is_new=True)
    except Exception:
        pass

    from .cache import cache
    cache.delete_match("stats_*")
    cache.delete_match("map_*")
    cache.delete_match("heatmap_*")
    cache.delete_match("ev_v2_*")
    return {"ok": True}

@router.patch("/admin/crowdsource/{report_id}/reject")
def reject_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    report = db.query(models.CrowdsourcedReport).filter(models.CrowdsourcedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.event_id:
        # If linked to an event, delete the event which recursively rejects the report via _delete_event_internal
        ev = db.query(models.Event).filter(models.Event.id == report.event_id).first()
        if ev:
            from .api import _delete_event_internal
            _delete_event_internal(db, ev)
            # [FIX] Clear event_id so if we re-approve, it creates a new event
            report.status = "rejected"
            report.event_id = None
            db.commit()
            return {"ok": True, "message": "Report rejected and associated event deleted."}
            
    report.status = "rejected"
    report.event_id = None # Ensure clean state
    db.commit()
    
    log_audit("reject_report", admin.id, admin.email, details={"report_id": report_id})
    
    from .cache import cache
    cache.delete_match("stats_*")
    return {"ok": True}
@router.get("/admin/crowdsource/export")
def export_crowdsource_reports(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db), 
    admin: models.User = Depends(auth.get_current_admin)
):
    import pandas as pd
    import io
    from fastapi.responses import StreamingResponse
    from sqlalchemy import and_

    query = db.query(models.CrowdsourcedReport)
    if start_date or end_date:
        d_start, d_end = get_date_range(0, None, start_date, end_date)
        query = query.filter(models.CrowdsourcedReport.created_at >= d_start, models.CrowdsourcedReport.created_at < d_end)
            
    reports = query.order_by(models.CrowdsourcedReport.created_at.desc()).all()
    
    STATUS_MAP = {
        "pending": "Chờ duyệt",
        "approved": "Đã duyệt", 
        "rejected": "Từ chối"
    }

    data = []
    for r in reports:
        data.append({
            "ID": r.id,
            "Người gửi": r.name or "Khách",
            "SĐT": r.phone or "",
            "Tỉnh": r.province,
            "Địa chỉ": r.address or "",
            "Mô tả": r.description,
            "Tọa độ": f"{r.lat}, {r.lon}" if r.lat and r.lon else "",
            "Thời gian": r.created_at.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=7))).strftime("%H:%M:%S %d/%m/%Y") if r.created_at else "",
            "Trạng thái": STATUS_MAP.get(r.status, r.status)
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    sheet_name = 'Báo cáo hiện trường'
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        # [OPTIMIZATION] Auto-adjust column widths
        worksheet = writer.sheets[sheet_name]
        from openpyxl.utils import get_column_letter
        for i, column in enumerate(df.columns):
            col_data_len = df[column].astype(str).map(len).max() if not df[column].empty else 0
            col_header_len = len(str(column))
            adjusted_width = min(max(col_data_len, col_header_len) + 3, 60)
            worksheet.column_dimensions[get_column_letter(i + 1)].width = adjusted_width

    output.seek(0)
    
    headers = {'Content-Disposition': 'attachment; filename="bao-cao-hien-truong.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/rescue/hotlines", response_model=List[schemas.RescueHotlineOut])
def get_rescue_hotlines(
    limit: int = 1000,
    province: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.RescueHotline)
    if province and province != "Toàn quốc":
        # [FIX] Always include "Toàn quốc" so National Hotlines don't disappear in Frontend
        query = query.filter(
            (models.RescueHotline.province == province) | 
            (models.RescueHotline.province == "Toàn quốc")
        )
    
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (models.RescueHotline.agency.ilike(search_filter)) | 
            (models.RescueHotline.phone.ilike(search_filter)) |
            (models.RescueHotline.address.ilike(search_filter)) |
            (models.RescueHotline.province.ilike(search_filter))
        )
        
    return query.order_by(models.RescueHotline.province.asc(), models.RescueHotline.agency.asc()).limit(limit).all()

@router.post("/admin/rescue", response_model=schemas.RescueHotlineOut)
def create_rescue_hotline(
    payload: schemas.RescueHotlineCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    hotline = models.RescueHotline(**payload.model_dump())
    db.add(hotline)
    db.commit()
    db.refresh(hotline)
    return hotline

@router.put("/admin/rescue/{hotline_id}", response_model=schemas.RescueHotlineOut)
def update_rescue_hotline(
    hotline_id: int,
    payload: schemas.RescueHotlineUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    hotline = db.query(models.RescueHotline).filter(models.RescueHotline.id == hotline_id).first()
    if not hotline:
        raise HTTPException(status_code=404, detail="Hotline not found")
        
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(hotline, k, v)
        
    db.commit()
    db.refresh(hotline)
    return hotline

@router.delete("/admin/rescue/{hotline_id}", status_code=204)
def delete_rescue_hotline(
    hotline_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    rows = db.query(models.RescueHotline).filter(models.RescueHotline.id == hotline_id).delete()
    if rows == 0:
        raise HTTPException(status_code=404, detail="Hotline not found")
        
    db.commit()
    return
