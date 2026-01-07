from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash

db = SessionLocal()
user = db.query(User).filter(User.email == "admin@vdw.com").first()
if user:
    new_hash = get_password_hash("admin123")
    user.hashed_password = new_hash
    db.commit()
    print(f"Password for {user.email} reset to 'admin123'")
    print(f"New hash prefix: {new_hash[:15]}")
else:
    print("User admin@vdw.com not found")
