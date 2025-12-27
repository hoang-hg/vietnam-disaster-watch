import logging
from sqlalchemy.orm import Session
from . import models
from datetime import datetime

logger = logging.getLogger(__name__)

def notify_followers_of_article(db: Session, event: models.Event, article: models.Article):
    """
    Thông báo cho những người đang theo dõi sự kiện về bài báo mới.
    """
    try:
        # Get followers
        followers = db.query(models.EventFollow).filter(models.EventFollow.event_id == event.id).all()
        if not followers:
            return

        for follow in followers:
            # Create in-app notification
            notif = models.Notification(
                user_id=follow.user_id,
                type="new_article",
                title=f"Cập nhật mới cho: {event.title[:50]}...",
                message=f"Báo {article.source} vừa đăng: {article.title[:100]}...",
                link=f"/events/{event.id}",
                created_at=datetime.utcnow()
            )
            db.add(notif)
        
        db.commit()
    except Exception as e:
        logger.error(f"Error notifying followers: {e}")
        db.rollback()

def notify_users_of_event(db: Session, event: models.Event):
    """
    Thông báo sự kiện mới cho người dùng quan tâm đến tỉnh thành đó.
    """
    try:
        # Get users who favor this province
        users = db.query(models.User).filter(models.User.favorite_province == event.province).all()
        for user in users:
            notif = models.Notification(
                user_id=user.id,
                type="new_event",
                title=f"Sự kiện mới tại {event.province}",
                message=f"Hệ thống ghi nhận: {event.title}",
                link=f"/events/{event.id}",
                created_at=datetime.utcnow()
            )
            db.add(notif)
        db.commit()
    except Exception as e:
        logger.error(f"Error notifying users of new event: {e}")
        db.rollback()

async def send_system_health_alert(status_message: str):
    """
    Thông báo tình trạng hệ thống.
    """
    pass
