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
    current_user: models.User = Depends(auth.get_current_user)
):
    db_report = models.CrowdsourcedReport(
        user_id=current_user.id,
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
