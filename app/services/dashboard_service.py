from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from models.models import User, UserType, UserActivity, Transaction, TransactionType, Wallet, Activity, Template
from models.ticket_models import Ticket, TicketStatus
from core.logging import get_logger

logger = get_logger(__name__)


class DashboardService:
    """Service for dashboard statistics and analytics"""
    
    @staticmethod
    async def get_dashboard_stats(
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        db: AsyncSession
    ) -> Dict:
        """
        Get comprehensive dashboard statistics for Super Admin.
        Includes user counts, activity stats, and revenue data.
        """
        # Total users count by type
        total_users_result = await db.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar()
        
        enterprise_users_result = await db.execute(
            select(func.count(User.id))
            .where(User.user_type == UserType.ENTERPRISE)
        )
        total_enterprise_users = enterprise_users_result.scalar()
        
        individual_users_result = await db.execute(
            select(func.count(User.id))
            .where(User.user_type == UserType.INDIVIDUAL)
        )
        total_individual_users = individual_users_result.scalar()
        
        sub_users_result = await db.execute(
            select(func.count(User.id))
            .where(User.user_type == UserType.SUB_USER)
        )
        total_sub_users = sub_users_result.scalar()
        
        # Activity stats with date filter
        activity_query = select(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count')
        )
        
        if start_date:
            activity_query = activity_query.where(UserActivity.created_at >= start_date)
        if end_date:
            activity_query = activity_query.where(UserActivity.created_at <= end_date)
        
        activity_query = activity_query.group_by(UserActivity.activity_type)
        
        activity_result = await db.execute(activity_query)
        activities = activity_result.all()
        
        total_reports = 0
        total_forms = 0
        
        for activity_type, count in activities:
            if activity_type == "report_generated":
                total_reports = count
            elif activity_type == "form_downloaded":
                total_forms = count
        
        # Revenue calculation from wallet transactions
        revenue_query = select(
            func.sum(Transaction.amount)
        ).where(
            and_(
                Transaction.transaction_type == TransactionType.CREDIT,
                Transaction.purpose == "wallet_topup"
            )
        )
        
        if start_date:
            revenue_query = revenue_query.where(Transaction.created_at >= start_date)
        if end_date:
            revenue_query = revenue_query.where(Transaction.created_at <= end_date)
        
        revenue_result = await db.execute(revenue_query)
        total_revenue = revenue_result.scalar() or 0.0
        
        # Ticket statistics
        ticket_query = select(func.count(Ticket.id))
        if start_date:
            ticket_query = ticket_query.where(Ticket.created_at >= start_date)
        if end_date:
            ticket_query = ticket_query.where(Ticket.created_at <= end_date)
        
        total_tickets_result = await db.execute(ticket_query)
        total_tickets = total_tickets_result.scalar() or 0
        
        open_tickets_result = await db.execute(
            ticket_query.where(Ticket.status == TicketStatus.OPEN)
        )
        open_tickets = open_tickets_result.scalar() or 0
        
        resolved_tickets_result = await db.execute(
            ticket_query.where(Ticket.status == TicketStatus.RESOLVED)
        )
        resolved_tickets = resolved_tickets_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "total_enterprise_users": total_enterprise_users,
            "total_individual_users": total_individual_users,
            "total_sub_users": total_sub_users,
            "total_reports_generated": total_reports,
            "total_forms_downloaded": total_forms,
            "total_revenue": float(total_revenue),
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets
        }
    
    @staticmethod
    async def get_enterprise_users_summary(
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> tuple[List[Dict], int]:
        """
        Get detailed summary of all enterprise users.
        Includes sub-user counts, activity stats, and wallet balance.
        """
        # Get total enterprise users count
        count_result = await db.execute(
            select(func.count(User.id))
            .where(User.user_type == UserType.ENTERPRISE)
        )
        total = count_result.scalar()
        
        # Get enterprise users
        result = await db.execute(
            select(User)
            .where(User.user_type == UserType.ENTERPRISE)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        enterprise_users = result.scalars().all()
        
        summaries = []
        for user in enterprise_users:
            # Get sub-user count
            sub_user_result = await db.execute(
                select(func.count(User.id))
                .where(
                    and_(
                        User.user_type == UserType.SUB_USER,
                        User.enterprise_id == user.enterprise_id
                    )
                )
            )
            sub_user_count = sub_user_result.scalar()
            
            # Get activity stats for this enterprise and all sub-users
            user_ids_result = await db.execute(
                select(User.id).where(
                    or_(
                        and_(
                            User.user_type == UserType.ENTERPRISE,
                            User.enterprise_id == user.enterprise_id
                        ),
                        and_(
                            User.user_type == UserType.SUB_USER,
                            User.enterprise_id == user.enterprise_id
                        )
                    )
                )
            )
            user_ids = [row[0] for row in user_ids_result.all()]
            
            # Get activity counts
            activity_result = await db.execute(
                select(
                    UserActivity.activity_type,
                    func.count(UserActivity.id).label('count')
                )
                .where(UserActivity.user_id.in_(user_ids))
                .group_by(UserActivity.activity_type)
            )
            activities = activity_result.all()
            
            reports_generated = 0
            forms_downloaded = 0
            
            for activity_type, count in activities:
                if activity_type == "report_generated":
                    reports_generated = count
                elif activity_type == "form_downloaded":
                    forms_downloaded = count
            
            # Get wallet balance
            wallet_result = await db.execute(
                select(Wallet.balance).where(Wallet.user_id == user.id)
            )
            wallet_balance = wallet_result.scalar() or 0.0
            
            summaries.append({
                "id": user.id,
                "enterprise_id": user.enterprise_id,
                "full_name": user.full_name,
                "email": user.email,
                "sub_user_count": sub_user_count,
                "reports_generated": reports_generated,
                "forms_downloaded": forms_downloaded,
                "wallet_balance": float(wallet_balance),
                "is_active": user.is_active,
                "is_blocked": user.is_blocked,
                "created_at": user.created_at
            })
        
        return summaries, total
    
    @staticmethod
    async def get_revenue_by_period(
        period: str,  # 'daily', 'monthly', 'yearly'
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        db: AsyncSession
    ) -> List[Dict]:
        """
        Get revenue statistics grouped by time period.
        Supports daily, monthly, and yearly aggregation.
        """
        # Base query for revenue transactions
        query = select(Transaction).where(
            and_(
                Transaction.transaction_type == TransactionType.CREDIT,
                Transaction.purpose == "wallet_topup"
            )
        )
        
        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        # Group by period
        revenue_data = {}
        
        for txn in transactions:
            if period == 'daily':
                key = txn.created_at.strftime('%Y-%m-%d')
            elif period == 'monthly':
                key = txn.created_at.strftime('%Y-%m')
            elif period == 'yearly':
                key = txn.created_at.strftime('%Y')
            else:
                key = 'total'
            
            if key not in revenue_data:
                revenue_data[key] = {
                    'period': key,
                    'revenue': 0.0,
                    'transaction_count': 0
                }
            
            revenue_data[key]['revenue'] += txn.amount
            revenue_data[key]['transaction_count'] += 1
        
        # Convert to list and sort
        result_list = list(revenue_data.values())
        result_list.sort(key=lambda x: x['period'], reverse=True)
        
        return result_list
    
    @staticmethod
    async def get_user_growth_stats(
        period_days: int,
        db: AsyncSession
    ) -> Dict:
        """
        Get user registration growth statistics over specified period.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Users registered in period
        result = await db.execute(
            select(
                User.user_type,
                func.count(User.id).label('count')
            )
            .where(User.created_at >= start_date)
            .group_by(User.user_type)
        )
        
        growth_stats = {
            "period_days": period_days,
            "start_date": start_date,
            "end_date": end_date,
            "new_users_by_type": {}
        }
        
        for user_type, count in result.all():
            growth_stats["new_users_by_type"][user_type.value] = count
        
        return growth_stats
    
    @staticmethod
    async def get_top_active_users(
        limit: int,
        activity_type: Optional[str],
        db: AsyncSession
    ) -> List[Dict]:
        """
        Get most active users based on activity count.
        """
        query = select(
            UserActivity.user_id,
            func.count(UserActivity.id).label('activity_count'),
            func.sum(UserActivity.cost).label('total_cost')
        )
        
        if activity_type:
            query = query.where(UserActivity.activity_type == activity_type)
        
        query = (
            query
            .group_by(UserActivity.user_id)
            .order_by(func.count(UserActivity.id).desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        top_users_data = result.all()
        
        # Get user details
        top_users = []
        for user_id, activity_count, total_cost in top_users_data:
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                top_users.append({
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "user_type": user.user_type.value,
                    "activity_count": activity_count,
                    "total_cost": float(total_cost or 0)
                })
        
        return top_users
