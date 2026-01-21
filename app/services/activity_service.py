from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from models.models import UserActivity, User, UserType, TransactionPurpose
from core.config import settings
from core.logging import get_logger
from services.wallet_service import WalletService
from fastapi import HTTPException, status
import json

logger = get_logger(__name__)


class ActivityService:
    """Service for tracking and managing user activities"""
    
    ACTIVITY_COSTS = {
        "report_generated": settings.REPORT_GENERATION_COST,
        "form_downloaded": settings.FORM_DOWNLOAD_COST,
    }
    
    @staticmethod
    async def record_activity(
        user_id: int,
        activity_type: str,
        meta_data: Optional[Dict] = None,
        db: AsyncSession = None
    ) -> UserActivity:
        """
        Record user activity and deduct cost from wallet if applicable.
        Supports both report generation and form download tracking.
        """
        # Get activity cost
        cost = ActivityService.ACTIVITY_COSTS.get(activity_type, 0.0)
        
        # Check wallet balance if cost > 0
        if cost > 0:
            has_balance = await WalletService.check_sufficient_balance(
                user_id, cost, db
            )
            if not has_balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient wallet balance for {activity_type}"
                )
            
            # Deduct from wallet
            purpose_map = {
                "report_generated": TransactionPurpose.REPORT_GENERATION,
                "form_downloaded": TransactionPurpose.FORM_DOWNLOAD
            }
            
            await WalletService.deduct_funds(
                user_id=user_id,
                amount=cost,
                purpose=purpose_map.get(activity_type, TransactionPurpose.ADJUSTMENT),
                description=f"Cost for {activity_type}",
                db=db
            )
        
        # Create activity record
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            activity_count=1,
            cost=cost,
            meta_data=json.dumps(meta_data) if meta_data else None
        )
        
        db.add(activity)
        await db.commit()
        await db.refresh(activity)
        
        logger.info(f"Activity recorded: {activity_type} for user_id {user_id}")
        return activity
    
    @staticmethod
    async def get_user_activities(
        user_id: int,
        activity_type: Optional[str],
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> tuple[List[UserActivity], int]:
        """Get user's activity history with pagination"""
        # Build query
        query = select(UserActivity).where(UserActivity.user_id == user_id)
        
        if activity_type:
            query = query.where(UserActivity.activity_type == activity_type)
        
        # Get total count
        count_query = select(func.count(UserActivity.id)).where(
            UserActivity.user_id == user_id
        )
        if activity_type:
            count_query = count_query.where(UserActivity.activity_type == activity_type)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get activities
        query = query.order_by(UserActivity.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        activities = result.scalars().all()
        
        return list(activities), total
    
    @staticmethod
    async def get_activity_stats(
        user_id: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        db: AsyncSession
    ) -> Dict:
        """Get activity statistics for a user"""
        # Build base query
        query = select(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count'),
            func.sum(UserActivity.cost).label('total_cost')
        ).where(UserActivity.user_id == user_id)
        
        # Add date filters
        if start_date:
            query = query.where(UserActivity.created_at >= start_date)
        if end_date:
            query = query.where(UserActivity.created_at <= end_date)
        
        query = query.group_by(UserActivity.activity_type)
        
        result = await db.execute(query)
        stats = result.all()
        
        # Format response
        activity_stats = {}
        for activity_type, count, total_cost in stats:
            activity_stats[activity_type] = {
                "count": count,
                "total_cost": float(total_cost or 0)
            }
        
        return activity_stats
    
    @staticmethod
    async def get_enterprise_activity_summary(
        enterprise_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        db: AsyncSession
    ) -> Dict:
        """
        Get activity summary for entire enterprise including all sub-users.
        Used for enterprise dashboard.
        """
        # Get all users in enterprise
        result = await db.execute(
            select(User.id).where(
                or_(
                    and_(
                        User.user_type == UserType.ENTERPRISE,
                        User.enterprise_id == enterprise_id
                    ),
                    and_(
                        User.user_type == UserType.SUB_USER,
                        User.enterprise_id == enterprise_id
                    )
                )
            )
        )
        user_ids = [row[0] for row in result.all()]
        
        if not user_ids:
            return {
                "total_reports": 0,
                "total_forms": 0,
                "total_cost": 0.0,
                "sub_users_count": 0
            }
        
        # Build query
        query = select(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count'),
            func.sum(UserActivity.cost).label('total_cost')
        ).where(UserActivity.user_id.in_(user_ids))
        
        # Add date filters
        if start_date:
            query = query.where(UserActivity.created_at >= start_date)
        if end_date:
            query = query.where(UserActivity.created_at <= end_date)
        
        query = query.group_by(UserActivity.activity_type)
        
        result = await db.execute(query)
        stats = result.all()
        
        # Calculate totals
        total_reports = 0
        total_forms = 0
        total_cost = 0.0
        
        for activity_type, count, cost in stats:
            if activity_type == "report_generated":
                total_reports = count
            elif activity_type == "form_downloaded":
                total_forms = count
            total_cost += float(cost or 0)
        
        # Get sub-users count
        sub_users_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.user_type == UserType.SUB_USER,
                    User.enterprise_id == enterprise_id
                )
            )
        )
        sub_users_count = sub_users_result.scalar()
        
        return {
            "total_reports": total_reports,
            "total_forms": total_forms,
            "total_cost": total_cost,
            "sub_users_count": sub_users_count
        }
    
    @staticmethod
    async def get_sub_user_activities(
        sub_user_id: int,
        activity_type: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        db: AsyncSession
    ) -> Dict:
        """Get detailed activity breakdown for a specific sub-user"""
        query = select(UserActivity).where(UserActivity.user_id == sub_user_id)
        
        if activity_type:
            query = query.where(UserActivity.activity_type == activity_type)
        if start_date:
            query = query.where(UserActivity.created_at >= start_date)
        if end_date:
            query = query.where(UserActivity.created_at <= end_date)
        
        result = await db.execute(query)
        activities = result.scalars().all()
        
        # Aggregate stats
        report_count = sum(1 for a in activities if a.activity_type == "report_generated")
        form_count = sum(1 for a in activities if a.activity_type == "form_downloaded")
        total_cost = sum(a.cost for a in activities)
        
        return {
            "reports_generated": report_count,
            "forms_downloaded": form_count,
            "total_cost": float(total_cost),
            "activity_count": len(activities)
        }
