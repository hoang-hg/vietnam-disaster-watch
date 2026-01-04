from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas, auth
from datetime import datetime
from typing import List

router = APIRouter(prefix="/api/user", tags=["user"])

# Crowdsourcing
@router.post("/crowdsource/submit", response_model=schemas.CrowdsourcedReportOut)
def submit_report(
    report: schemas.CrowdsourcedReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(auth.get_current_user_optional)
):
    db_report = models.CrowdsourcedReport(
        user_id=current_user.id if current_user else None,
        **report.model_dump()
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@router.get("/crowdsource/approved", response_model=List[schemas.CrowdsourcedReportOut])
def get_approved_reports(db: Session = Depends(get_db)):
    return db.query(models.CrowdsourcedReport).filter(models.CrowdsourcedReport.status == "approved").all()

# Event Following
@router.post("/events/{event_id}/follow")
def toggle_follow_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    follow = db.query(models.EventFollow).filter(
        models.EventFollow.user_id == current_user.id,
        models.EventFollow.event_id == event_id
    ).first()
    
    if follow:
        db.delete(follow)
        db.commit()
        return {"status": "unfollowed"}
    else:
        # Check if event exists
        ev = db.query(models.Event).filter(models.Event.id == event_id).first()
        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")
        
        db_follow = models.EventFollow(user_id=current_user.id, event_id=event_id)
        db.add(db_follow)
        db.commit()
        return {"status": "followed"}

@router.get("/events/followed", response_model=List[schemas.EventOut])
def get_followed_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    follows = db.query(models.EventFollow).filter(models.EventFollow.user_id == current_user.id).all()
    event_ids = [f.event_id for f in follows]
    if not event_ids:
        return []
    events = db.query(models.Event).filter(models.Event.id.in_(event_ids)).all()
    return events

@router.get("/events/{event_id}/is-following")
def check_is_following(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    follow = db.query(models.EventFollow).filter(
        models.EventFollow.user_id == current_user.id,
        models.EventFollow.event_id == event_id
    ).first()
    return {"is_following": follow is not None}

# Notifications
@router.get("/notifications", response_model=List[schemas.NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(50).all()

@router.get("/notifications/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    return {"count": count}

@router.patch("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notif.is_read = True
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
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.get_current_admin)
):
    return db.query(models.CrowdsourcedReport).filter(models.CrowdsourcedReport.status == "pending").all()

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
    
    # Notify user
    notif = models.Notification(
        user_id=report.user_id,
        type="report_approved",
        title="Đóng góp đã được duyệt",
        message=f"Thông tin tại {report.province or 'hiện trường'} của bạn đã được Admin duyệt và hiển thị trên bản đồ.",
        link="/map",
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
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
    
    report.status = "rejected"
    db.commit()
    return {"ok": True}

@router.get("/admin/crowdsource/export")
async def export_crowdsource_reports(db: Session = Depends(get_db), admin: models.User = Depends(auth.get_current_admin)):
    import pandas as pd
    import io
    from fastapi.responses import StreamingResponse

    reports = db.query(models.CrowdsourcedReport).all()
    
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
            "Thời gian": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            "Trạng thái": r.status
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Báo cáo hiện trường')
    output.seek(0)
    
    headers = {'Content-Disposition': 'attachment; filename="bao-cao-hien-truong.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/rescue/hotlines", response_model=List[schemas.RescueHotlineOut])
def get_rescue_hotlines(
    limit: int = 1000,
    province: str | None = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.RescueHotline)
    if province:
        q = q.filter(models.RescueHotline.province == province)
    return q.limit(limit).all()

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
    hotline = db.query(models.RescueHotline).filter(models.RescueHotline.id == hotline_id).first()
    if not hotline:
        raise HTTPException(status_code=404, detail="Hotline not found")
        
    db.delete(hotline)
    db.commit()
    return
