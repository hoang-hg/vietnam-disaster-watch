from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash
from app.settings import settings

db = SessionLocal()
target_email = "admin@vdw.com"
target_pass = "Admin@123456"

user = db.query(User).filter(User.email == target_email).first()
if user:
    new_hash = get_password_hash(target_pass)
    user.hashed_password = new_hash
    db.commit()
    print(f"SUCCESS: Password for {user.email} has been reset to: {target_pass}")
else:
    print(f"ERROR: User {target_email} not found in database (PostgreSQL connection check successful).")
