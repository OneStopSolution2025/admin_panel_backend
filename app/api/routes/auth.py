"""
Authentication Routes - FULLY FIXED
Supports: 
- Strong Password Validation
- JSON Login for Frontend
- Signup Bonus Wallet Creation
- Activity Logging (FIXED)
- Token Refreshing (is_revoked fix)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import logging
import secrets

from core.database import get_db
from core.security import verify_password, get_password_hash, create_access_token
from core.config import settings
from models.models import User, Wallet, UserType, RefreshToken, UserActivity

# Initialize Router
router = APIRouter()
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ==========================================================
# PYDANTIC SCHEMAS
# ==========================================================

class UserRegistrationRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone_number: Optional[str] = None
    user_type: str = "individual"
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v
    
    @validator("user_type")
    def validate_user_type(cls, v):
        valid_types = ["individual", "enterprise", "super_admin"]
        if v not in valid_types:
            raise ValueError(f"Invalid user type. Must be one of: {', '.join(valid_types)}")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    user_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# ==========================================================
# ROUTES
# ==========================================================

@router.post("/register", response_model=dict)
async def register(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register new user with wallet bonus and activity logging"""
    
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # 1. Create User object
        hashed_pw = get_password_hash(request.password)
        user_type_map = {
            "individual": UserType.INDIVIDUAL,
            "enterprise": UserType.ENTERPRISE,
            "super_admin": UserType.SUPER_ADMIN
        }
        
        new_user = User(
            email=request.email,
            hashed_password=hashed_pw,
            full_name=request.full_name,
            user_type=user_type_map[request.user_type],
            is_active=True,
            is_blocked=False
        )
        db.add(new_user)
        db.flush() # Flushes to get new_user.id
        
        # 2. Create Wallet
        signup_bonus = 10.0
        new_wallet = Wallet(user_id=new_user.id, balance=signup_bonus)
        db.add(new_wallet)
        
        # 3. Log Activity - FIXED: Use correct field names
        activity = UserActivity(
            user_id=new_user.id,
            activity_type="USER_REGISTERED",  # ✅ FIXED: was action_type
            activity_count=1,
            cost=0.0,
            meta_data={"email": request.email, "signup_bonus": signup_bonus}  # ✅ ADDED: Use meta_data instead of description
        )
        db.add(activity)
        
        # 4. Final Commit and Refresh
        db.commit()
        db.refresh(new_user) 
        
        logger.info(f"✅ User registered: {new_user.email}")
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "user_type": new_user.user_type.value,
                "wallet_balance": signup_bonus
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=UserLoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Standard JSON login"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.is_active or user.is_blocked:
        raise HTTPException(status_code=403, detail="Account restricted")

    # Generate Access Token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "user_type": user.user_type.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Generate & Store Refresh Token
    refresh_token_str = secrets.token_urlsafe(32)
    new_refresh = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False
    )
    db.add(new_refresh)
    db.commit()

    return UserLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        user_type=user.user_type.value
    )

@router.post("/refresh")
async def refresh_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Refresh the access token (Fixed is_revoked attribute error)"""
    token_record = db.query(RefreshToken).filter(
        RefreshToken.token == request.refresh_token,
        RefreshToken.is_revoked == False
    ).first()
    
    if not token_record or token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User unavailable")

    new_access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "user_type": user.user_type.value}
    )
    
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(refresh_token: str, db: Session = Depends(get_db)):
    """Revoke refresh token on logout"""
    token_record = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if token_record:
        token_record.is_revoked = True
        db.commit()
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get profile info using the Bearer token"""
    from jose import jwt
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "user_type": user.user_type.value,
            "is_active": user.is_active
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")
