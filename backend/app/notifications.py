import logging
from sqlalchemy.orm import Session
from . import models
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def notify_followers_of_article(db: Session, event: models.Event, article: models.Article):
    """
    Thông báo cho những người đang theo dõi sự kiện về bài báo mới.
    """
    try:
        # Get followers (IDs only for performance)
        follower_ids = db.query(models.EventFollow.user_id).filter(models.EventFollow.event_id == event.id).all()
        if not follower_ids:
            return

        notifications = []
        # Safe slice for title and handle potential None
        event_title = (event.title or "")[:50]
        article_title = (article.title or "")[:100]
        source_name = article.source or "Nguồn tin"

        for (user_id,) in follower_ids:
            notif = models.Notification(
                user_id=user_id,
                type="new_article",
                title=f"Cập nhật mới: {event_title}...",
                message=f"Báo {source_name} vừa đăng: {article_title}...",
                link=f"/events/{event.id}",
                created_at=datetime.now(timezone.utc)
            )
            notifications.append(notif)
        
        # Optimization: Bulk insert for performance
        if notifications:
            db.bulk_save_objects(notifications)
            
    except Exception as e:
        logger.error(f"Error notifying followers: {e}")
        pass


def notify_users_of_event(db: Session, event: models.Event):
    """
    Thông báo sự kiện mới cho người dùng quan tâm đến tỉnh thành đó.
    """
    # Quick exit if province is invalid or unknown
    if not event.province or event.province.lower() == "unknown":
        return

    try:
        # Get users who favor this province (IDs only)
        user_ids = db.query(models.User.id).filter(models.User.favorite_province == event.province).all()
        if not user_ids:
            return

        notifications = []
        event_title = (event.title or "")[:100]

        for (user_id,) in user_ids:
            notif = models.Notification(
                user_id=user_id,
                type="new_event",
                title=f"Sự kiện mới tại {event.province}",
                message=f"Hệ thống ghi nhận: {event_title}",
                link=f"/events/{event.id}",
                created_at=datetime.now(timezone.utc)
            )
            notifications.append(notif)
            
        # Optimization: Bulk insert for performance
        if notifications:
            db.bulk_save_objects(notifications)
            
    except Exception as e:
        logger.error(f"Error notifying users of new event: {e}")
        pass
