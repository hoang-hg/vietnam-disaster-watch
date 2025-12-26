import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from . import settings, models
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

def send_disaster_alert(user_email: str, event: models.Event):
    """Sends a disaster alert email to a user."""
    # Note: In a real production app, use an async task queue like Celery or RQ.
    # For now, we'll implement the logic with a placeholder for SMTP configuration.
    
    s = settings.settings
    if not s.smtp_host or not s.smtp_user:
        logger.warning(f"SMTP not configured. Skipping alert to {user_email} for event {event.id}")
        return

    msg = MIMEMultipart()
    msg['From'] = f"Viet Disaster Watch <{s.smtp_user}>"
    msg['To'] = user_email
    msg['Subject'] = f"🚨 CẢNH BÁO THIÊN TAI: {event.title.upper()}"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; overflow: hidden;">
            <div style="background-color: #e53e3e; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">CẢNH BÁO THIÊN TAI MỚI</h1>
            </div>
            <div style="padding: 20px;">
                <p>Xin chào,</p>
                <p>Hệ thống ghi nhận một sự kiện thiên tai mới tại khu vực bạn theo dõi (<strong>{event.province}</strong>):</p>
                
                <div style="background-color: #f7fafc; padding: 15px; border-radius: 5px; border-left: 5px solid #e53e3e; margin: 20px 0;">
                    <h2 style="margin-top: 0; color: #2d3748;">{event.title}</h2>
                    <p><strong>Loại hình:</strong> {event.disaster_type}</p>
                    <p><strong>Thời gian:</strong> {event.started_at.strftime('%H:%M %d/%m/%Y')}</p>
                </div>
                
                <p>Vui lòng truy cập hệ thống để xem chi tiết và các hướng dẫn ứng phó:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://viet-disaster.gov.vn/events/{event.id}" 
                       style="background-color: #3182ce; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                       XEM CHI TIẾT SỰ KIỆN
                    </a>
                </div>
                
                <p style="font-size: 12px; color: #718096; border-top: 1px solid #edf2f7; pt: 15px;">
                    Bạn nhận được thông báo này vì đã đăng ký theo dõi tại tỉnh {event.province}. 
                    Bạn có thể tắt thông báo trong phần Cài đặt tài khoản.
                </p>
            </div>
            <div style="background-color: #f7fafc; padding: 10px; text-align: center; font-size: 11px; color: #a0aec0;">
                © 2024 Viet Disaster Watch - Hệ thống giám sát thiên tai thời gian thực
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port) as server:
            if s.smtp_tls:
                server.starttls()
            server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
        logger.info(f"Alert sent to {user_email} for event {event.id}")
    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {str(e)}")

def notify_users_of_event(db: Session, event: models.Event):
    """Finds users interested in this event's province and notifies them."""
    if not event.province:
        return

    users = db.query(models.User).filter(
        models.User.favorite_province == event.province,
        models.User.email_notifications == True
    ).all()

    for user in users:
        send_disaster_alert(user.email, event)
