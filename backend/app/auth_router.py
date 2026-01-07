from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from . import auth, models, database, settings
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    favorite_province: str | None = None

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None
    role: str
    favorite_province: str | None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

@router.post("/register", response_model=UserOut)
@limiter.limit("3/hour")  # Max 3 registrations per hour to prevent spam
async def register(request: Request, user_in: UserCreate, db: Session = Depends(auth.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Fixed Admin Accounts Configuration
    # Only these specific emails will be granted Admin privileges upon registration.
    # You can modify this list to change who gets admin access.
    FIXED_ADMIN_EMAILS = {
        "admin@vdw.com",
        "quantri@vdw.com", 
        "root@vdw.com" 
    }
    
    role = "user"
    if user_in.email in FIXED_ADMIN_EMAILS:
        role = "admin"

    hashed_pw = auth.get_password_hash(user_in.password)
    new_user = models.User(
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        role=role,
        favorite_province=user_in.favorite_province,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # Max 5 login attempts per minute to prevent brute force
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserOut)
@limiter.limit("20/minute")  # Reasonable limit for checking user info
async def read_users_me(request: Request, current_user: models.User = Depends(auth.get_current_user)):
    return current_user

class UserUpdate(BaseModel):
    favorite_province: str | None = None

@router.put("/me/preferences", response_model=UserOut)
def update_user_preferences(
    update_in: UserUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    """Allows user to update their monitoring preferences."""
    if update_in.favorite_province is not None:
        current_user.favorite_province = update_in.favorite_province
    db.commit()
    db.refresh(current_user)
    return current_user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password", status_code=200)
def change_password(
    payload: ChangePasswordRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    """Allows any logged-in user (admin or normal) to change their password."""
    # verify old password
    if not auth.verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng."
        )
    
    # update password
    current_user.hashed_password = auth.get_password_hash(payload.new_password)
    db.commit()
    
    return {"message": "Đổi mật khẩu thành công."}

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

@router.post("/reset-password", status_code=200)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(auth.get_db)
):
    """
    [INSECURE] Allows resetting password knowing only the email.
    Intended for development environments or closed internal tools without email service.
    """
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email không tồn tại trong hệ thống."
        )
    
    # Update password
    user.hashed_password = auth.get_password_hash(payload.new_password)
    db.commit()
    
    return {"message": "Mật khẩu đã được đặt lại thành công."}
