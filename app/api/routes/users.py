"""
User Management Routes - ENHANCED
Includes:
- Admin user creation (Answer to Question 1)
- Block/Unblock users (Answer to Question 2)
- User listing with filters
- User update and delete
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
import logging

from core.database import get_db
from api.deps import get_current_active_user
from core.security import get_password_hash
from models.models import User, UserType, UserActivity, Wallet

router = APIRouter()
logger = logging.getLogger(__name__)


# ==========================================================
# PYDANTIC SCHEMAS
# ==========================================================

class AdminUserCreate(BaseModel):
    """Schema for admin creating users"""
    email: EmailStr
    password: str
    full_name: str
    user_type: str = "individual"
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
    
    @validator("user_type")
    def validate_user_type(cls, v):
        valid_types = ["individual", "enterprise", "super_admin"]
        if v not in valid_types:
            raise ValueError(f"Invalid user type. Must be one of: {', '.join(valid_types)}")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user"""
    full_name: Optional[str] = None
    password: Optional[str] = None
    user_type: Optional[str] = None
    is_active: Optional[bool] = None


class BlockUserRequest(BaseModel):
    """Schema for block/unblock action"""
    block: bool  # True = block, False = unblock


# ==========================================================
# CURRENT USER INFO
# ==========================================================

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    wallet = current_user.wallet
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "user_type": current_user.user_type.value,
        "is_active": current_user.is_active,
        "is_blocked": current_user.is_blocked,
        "created_at": current_user.created_at,
        "wallet_balance": wallet.balance if wallet else 0.0
    }


# ==========================================================
# ADMIN: CREATE USER (Answer to Question 1)
# ==========================================================

@router.post("/admin/create", status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_data: AdminUserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Admin/Super Admin creates a new user
    - No email verification required
    - Can assign user types
    - Auto-creates wallet
    - Only accessible by admin/super_admin
    """
    # Permission check
    if current_user.user_type.value not in ["super_admin", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users"
        )
    
    # User type assignment validation
    if user_data.user_type in ["super_admin"] and current_user.user_type.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can create super_admin users"
        )
    
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Map user type
        user_type_map = {
            "individual": UserType.INDIVIDUAL,
            "enterprise": UserType.ENTERPRISE,
            "super_admin": UserType.SUPER_ADMIN
        }
        
        # Create user
        new_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            user_type=user_type_map[user_data.user_type],
            is_active=True,
            is_blocked=False
        )
        
        db.add(new_user)
        db.flush()
        
        # Auto-create wallet
        new_wallet = Wallet(user_id=new_user.id, balance=0.0)
        db.add(new_wallet)
        
        # Log activity
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="ADMIN_CREATE_USER",
            activity_count=1,
            cost=0.0,
            meta_data={
                "created_user_email": new_user.email,
                "created_user_type": new_user.user_type.value,
                "admin_email": current_user.email
            }
        )
        db.add(activity)
        
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"✅ Admin {current_user.email} created user: {new_user.email}")
        
        return {
            "success": True,
            "message": "User created successfully",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "user_type": new_user.user_type.value,
                "is_active": new_user.is_active,
                "created_at": new_user.created_at
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Admin user creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}"
        )


# ==========================================================
# ADMIN: BLOCK/UNBLOCK USER (Answer to Question 2)
# ==========================================================

@router.put("/{user_id}/block")
async def block_unblock_user(
    user_id: int,
    block_request: BlockUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Block or unblock a user
    
    Permissions:
    - Enterprise admin: Can block individual users only
    - Super_admin: Can block anyone including other admins
    
    Parameters:
    - block: true = block user, false = unblock user
    """
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Permission checks
    if current_user.user_type.value == "enterprise":
        # Enterprise admin can only block individual users
        if target_user.user_type.value in ["enterprise", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enterprise admins cannot block other admins or super_admins"
            )
    elif current_user.user_type.value == "super_admin":
        # Super admin can block anyone except themselves
        if target_user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block yourself"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to block users"
        )
    
    try:
        # Update block status
        target_user.is_blocked = block_request.block
        target_user.updated_at = datetime.utcnow()
        
        # Log activity
        action = "BLOCK_USER" if block_request.block else "UNBLOCK_USER"
        activity = UserActivity(
            user_id=current_user.id,
            activity_type=action,
            activity_count=1,
            cost=0.0,
            meta_data={
                "target_user_id": target_user.id,
                "target_user_email": target_user.email,
                "action": "blocked" if block_request.block else "unblocked",
                "admin_email": current_user.email
            }
        )
        db.add(activity)
        db.commit()
        
        logger.info(f"✅ User {target_user.email} {'blocked' if block_request.block else 'unblocked'} by {current_user.email}")
        
        return {
            "success": True,
            "message": f"User {'blocked' if block_request.block else 'unblocked'} successfully",
            "user_id": target_user.id,
            "email": target_user.email,
            "is_blocked": target_user.is_blocked
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Block/unblock error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Operation failed: {str(e)}"
        )


# ==========================================================
# ADMIN: GET ALL USERS
# ==========================================================

@router.get("/")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    user_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_blocked: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of users with filtering
    
    Filters:
    - user_type: Filter by user type (individual, enterprise, super_admin)
    - is_active: Filter by active status
    - is_blocked: Filter by blocked status
    - search: Search by email or name
    """
    # Permission check
    if current_user.user_type.value not in ["enterprise", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    query = db.query(User)
    
    # Apply filters
    if user_type:
        try:
            user_type_enum = UserType[user_type.upper()]
            query = query.filter(User.user_type == user_type_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user_type: {user_type}"
            )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if is_blocked is not None:
        query = query.filter(User.is_blocked == is_blocked)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_pattern)) | 
            (User.full_name.ilike(search_pattern))
        )
    
    # Get total count
    total = query.count()
    
    # Get users with pagination
    users = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type.value,
                "is_active": user.is_active,
                "is_blocked": user.is_blocked,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "wallet_balance": user.wallet.balance if user.wallet else 0.0
            }
            for user in users
        ]
    }


# ==========================================================
# ADMIN: GET SINGLE USER
# ==========================================================

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user by ID with detailed information"""
    
    # Permission check
    if current_user.user_type.value not in ["enterprise", "super_admin"]:
        # Regular users can only see their own profile
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get wallet info
    wallet = user.wallet
    
    # Get recent activities
    recent_activities = db.query(UserActivity).filter(
        UserActivity.user_id == user_id
    ).order_by(UserActivity.created_at.desc()).limit(5).all()
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type.value,
        "is_active": user.is_active,
        "is_blocked": user.is_blocked,
        "enterprise_id": user.enterprise_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": user.last_login,
        "wallet": {
            "balance": wallet.balance if wallet else 0.0,
            "created_at": wallet.created_at if wallet else None
        },
        "recent_activities": [
            {
                "id": activity.id,
                "activity_type": activity.activity_type,
                "activity_count": activity.activity_count,
                "cost": activity.cost,
                "created_at": activity.created_at
            }
            for activity in recent_activities
        ]
    }


# ==========================================================
# ADMIN: UPDATE USER
# ==========================================================

@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Admin updates user information"""
    
    # Permission check
    if current_user.user_type.value not in ["enterprise", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # User type change validation
    if user_update.user_type and user_update.user_type != target_user.user_type.value:
        if current_user.user_type.value != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super_admin can change user types"
            )
    
    try:
        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "password":
                target_user.hashed_password = get_password_hash(value)
            elif field == "user_type":
                user_type_map = {
                    "individual": UserType.INDIVIDUAL,
                    "enterprise": UserType.ENTERPRISE,
                    "super_admin": UserType.SUPER_ADMIN
                }
                target_user.user_type = user_type_map[value]
            else:
                setattr(target_user, field, value)
        
        target_user.updated_at = datetime.utcnow()
        
        # Log activity
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="ADMIN_UPDATE_USER",
            activity_count=1,
            cost=0.0,
            meta_data={
                "target_user_id": target_user.id,
                "target_user_email": target_user.email,
                "updated_fields": list(update_data.keys()),
                "admin_email": current_user.email
            }
        )
        db.add(activity)
        
        db.commit()
        db.refresh(target_user)
        
        logger.info(f"✅ User {target_user.email} updated by {current_user.email}")
        
        return {
            "success": True,
            "message": "User updated successfully",
            "user": {
                "id": target_user.id,
                "email": target_user.email,
                "full_name": target_user.full_name,
                "user_type": target_user.user_type.value,
                "is_active": target_user.is_active,
                "is_blocked": target_user.is_blocked
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ User update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )


# ==========================================================
# ADMIN: DELETE USER (Soft Delete)
# ==========================================================

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Admin deletes a user (soft delete - sets is_active = False)"""
    
    # Only super_admin can delete
    if current_user.user_type.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can delete users"
        )
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    try:
        # Soft delete
        target_user.is_active = False
        target_user.is_blocked = True
        target_user.updated_at = datetime.utcnow()
        
        # Log activity
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="ADMIN_DELETE_USER",
            activity_count=1,
            cost=0.0,
            meta_data={
                "deleted_user_id": target_user.id,
                "deleted_user_email": target_user.email,
                "admin_email": current_user.email
            }
        )
        db.add(activity)
        
        db.commit()
        
        logger.info(f"✅ User {target_user.email} deleted by {current_user.email}")
        
        return {
            "success": True,
            "message": "User deleted successfully",
            "user_id": user_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ User deletion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )
