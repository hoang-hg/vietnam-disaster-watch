from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from . import auth, models, database, settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
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
def register(user_in: UserCreate, db: Session = Depends(auth.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Initial logic: first user or email starting with "admin" can be admin
    # Constraint: Maximum 3 admin accounts
    admin_count = db.query(models.User).filter(models.User.role == "admin").count()
    is_first = db.query(models.User).count() == 0
    
    role = "user"
    if is_first or user_in.email.startswith("admin"):
        if admin_count < 3:
            role = "admin"
        else:
            # Fallback to "user" if admin limit (3) is reached
            role = "user"

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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
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
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

class UserUpdate(BaseModel):
    favorite_province: str | None = None

@router.put("/me/preferences", response_model=UserOut)
async def update_user_preferences(
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
