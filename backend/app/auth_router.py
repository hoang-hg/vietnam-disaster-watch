from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, model_validator
from . import auth, models, database, settings
from slowapi import Limiter
from slowapi.util import get_remote_address
from .auth import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
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
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký.")
    
    role = "user"
    if user_in.email in settings.settings.fixed_admin_emails:
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
@limiter.limit("10/minute")  # Slightly higher for valid users
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.email, "ver": user.token_version}, 
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user
    }

@router.post("/logout")
def logout(current_user: models.User = Depends(auth.get_current_user)):
    """
    Standard logout endpoint. While JWT is stateless, 
    this can be used for logging or future-proofing blocklists.
    """
    return {"message": "Đăng xuất thành công."}

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

class UserUpdate(BaseModel):
    favorite_province: str | None = None

@router.put("/me/preferences", response_model=UserOut)
def update_user_preferences(
    update_in: UserUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)  
):
    """Allows user to update their monitoring preferences."""
    if update_in.favorite_province is not None:
        current_user.favorite_province = update_in.favorite_province
    db.commit()
    db.refresh(current_user)
    return current_user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @model_validator(mode='after')
    def check_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Mật khẩu mới không khớp nhau.")
        return self

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
    
    if payload.current_password == payload.new_password:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới không được trùng với mật khẩu cũ."
        )

    # update password and increment version to invalidate other sessions/tokens
    current_user.hashed_password = auth.get_password_hash(payload.new_password)
    current_user.token_version += 1
    db.commit()
    
    return {"message": "Đổi mật khẩu thành công. Các phiên đăng nhập khác đã bị hủy."}

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @model_validator(mode='after')
    def check_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Mật khẩu xác nhận không khớp.")
        return self

@router.post("/reset-password", status_code=200)
@limiter.limit("5/hour")
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(auth.get_db)
):
    """
    Allows resetting password knowing the email.
    """
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài khoản với email này không tồn tại."
        )
    
    # Update password and increment version
    user.hashed_password = auth.get_password_hash(payload.new_password)
    user.token_version += 1
    db.commit()
    
    return {"message": "Mật khẩu đã được đặt lại thành công. Các phiên đăng nhập cũ đã hết hiệu lực."}
