from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from models.models import User, UserType, Wallet, RefreshToken
from schemas.schemas import UserCreate, UserUpdate
from core.security import security_manager
from core.config import settings
from core.logging import get_logger
from services.wallet_service import WalletService
from fastapi import HTTPException, status

logger = get_logger(__name__)


class UserService:
    """Service for user management operations"""
    
    @staticmethod
    async def create_user(user_data: UserCreate, db: AsyncSession) -> User:
        """
        Create a new user with wallet.
        Handles user ID generation based on user type.
        """
        # Check if email already exists
        existing = await UserService.get_user_by_email(user_data.email, db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = User(
            email=user_data.email,
            hashed_password=security_manager.get_password_hash(user_data.password),
            full_name=user_data.full_name,
            user_type=user_data.user_type,
            enterprise_id=user_data.enterprise_id,
            parent_user_id=user_data.parent_user_id,
            is_active=True,
            is_blocked=False
        )
        
        db.add(user)
        await db.flush()  # Get user.id without committing
        
        # Create wallet for user
        await WalletService.create_wallet(user.id, db)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User created: {user.id} ({user.user_type})")
        return user
    
    @staticmethod
    async def get_user_by_id(user_id: int, db: AsyncSession) -> Optional[User]:
        """Get user by database ID"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession
    ) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await UserService.get_user_by_email(email, db)
        if not user:
            return None
        
        if not security_manager.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active or user.is_blocked:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return user
    
    @staticmethod
    async def update_user(
        user_id: int,
        user_data: UserUpdate,
        db: AsyncSession
    ) -> User:
        """Update user information"""
        user = await UserService.get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User updated: {user.id}")
        return user
    
    @staticmethod
    async def block_user(user_id: int, db: AsyncSession) -> User:
        """Block a user"""
        user = await UserService.get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_blocked = True
        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User blocked: {user.id}")
        return user
    
    @staticmethod
    async def unblock_user(user_id: int, db: AsyncSession) -> User:
        """Unblock a user"""
        user = await UserService.get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_blocked = False
        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User unblocked: {user.id}")
        return user
    
    @staticmethod
    async def get_users(
        skip: int,
        limit: int,
        user_type: Optional[UserType],
        is_active: Optional[bool],
        db: AsyncSession
    ) -> tuple[List[User], int]:
        """Get users with filters and pagination"""
        # Build query
        query = select(User)
        conditions = []
        
        if user_type:
            conditions.append(User.user_type == user_type)
        if is_active is not None:
            conditions.append(User.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count(User.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get users
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        return list(users), total
    
    @staticmethod
    async def get_sub_users(
        enterprise_id: str,
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> tuple[List[User], int]:
        """Get sub-users for an enterprise"""
        # Get total count
        count_result = await db.execute(
            select(func.count(User.id))
            .where(
                and_(
                    User.user_type == UserType.SUB_USER,
                    User.enterprise_id == enterprise_id
                )
            )
        )
        total = count_result.scalar()
        
        # Get sub-users
        result = await db.execute(
            select(User)
            .where(
                and_(
                    User.user_type == UserType.SUB_USER,
                    User.enterprise_id == enterprise_id
                )
            )
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        sub_users = result.scalars().all()
        
        return list(sub_users), total
    
    @staticmethod
    async def create_refresh_token(user_id: int, db: AsyncSession) -> str:
        """Create and store refresh token"""
        # Generate refresh token
        token_data = {"sub": str(user_id)}
        expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        token = security_manager.create_refresh_token(token_data, expires)
        
        # Store in database
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + expires
        )
        
        db.add(refresh_token)
        await db.commit()
        
        return token
    
    @staticmethod
    async def revoke_refresh_token(token: str, db: AsyncSession):
        """Revoke a refresh token"""
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        refresh_token = result.scalar_one_or_none()
        
        if refresh_token:
            refresh_token.is_revoked = True
            await db.commit()
