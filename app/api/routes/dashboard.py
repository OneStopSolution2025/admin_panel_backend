"""
Dashboard Routes - ENHANCED (Answer to Question 4)
Provides detailed dashboard statistics for:
- Super Admin: Full system metrics
- Enterprise Admin: Organization metrics
- Individual Users: Personal stats
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from core.database import get_db
from api.deps import get_current_active_user
from models.models import User, Wallet, UserActivity, Transaction, UserType
from models.ticket_models import Ticket

router = APIRouter()
logger = logging.getLogger(__name__)


# ==========================================================
# SUPER ADMIN DASHBOARD
# ==========================================================

@router.get("/super-admin")
async def get_super_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Super Admin Dashboard - Full System Metrics
    
    Returns:
    - Total users (by user_type)
    - Active/Inactive/Blocked users
    - Total revenue (all wallets)
    - Transaction statistics
    - User growth analytics (last 7 days)
    - Support ticket statistics
    - Recent activities
    """
    if current_user.user_type.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access only"
        )
    
    try:
        # ==================== USER STATISTICS ====================
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True, User.is_blocked == False).count()
        inactive_users = db.query(User).filter(User.is_active == False).count()
        blocked_users = db.query(User).filter(User.is_blocked == True).count()
        
        # Users by type
        users_by_type = db.query(
            User.user_type,
            func.count(User.id).label('count')
        ).group_by(User.user_type).all()
        
        type_breakdown = {
            user_type.value: count 
            for user_type, count in users_by_type
        }
        
        # New users this month
        first_day_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users_this_month = db.query(User).filter(
            User.created_at >= first_day_of_month
        ).count()
        
        # ==================== WALLET & REVENUE STATISTICS ====================
        total_wallets = db.query(Wallet).count()
        total_balance = db.query(func.sum(Wallet.balance)).scalar() or 0
        
        # Total transactions
        total_transactions = db.query(Transaction).count()
        completed_transactions = db.query(Transaction).filter(
            Transaction.status == "completed"
        ).count()
        
        # Revenue this month
        revenue_this_month = db.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.created_at >= first_day_of_month,
            Transaction.transaction_type == "CREDIT",
            Transaction.status == "completed"
        ).scalar() or 0
        
        # ==================== ACTIVITY STATISTICS ====================
        total_activities = db.query(UserActivity).count()
        activities_this_month = db.query(UserActivity).filter(
            UserActivity.created_at >= first_day_of_month
        ).count()
        
        # Total cost from activities
        total_activity_cost = db.query(func.sum(UserActivity.cost)).scalar() or 0
        
        # ==================== SUPPORT TICKET STATISTICS ====================
        try:
            total_tickets = db.query(Ticket).count()
            open_tickets = db.query(Ticket).filter(
                Ticket.status.in_(["open", "in_progress"])
            ).count()
            closed_tickets = db.query(Ticket).filter(
                Ticket.status == "closed"
            ).count()
        except Exception:
            # If ticket table doesn't exist or has issues
            total_tickets = 0
            open_tickets = 0
            closed_tickets = 0
        
        # ==================== RECENT USERS ====================
        recent_users = db.query(User).order_by(
            desc(User.created_at)
        ).limit(10).all()
        
        # ==================== RECENT TRANSACTIONS ====================
        recent_transactions = db.query(Transaction).order_by(
            desc(Transaction.created_at)
        ).limit(10).all()
        
        # ==================== USER GROWTH (Last 7 days) ====================
        growth_data = []
        for i in range(6, -1, -1):
            date = datetime.utcnow() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            count = db.query(User).filter(
                User.created_at >= day_start,
                User.created_at < day_end
            ).count()
            
            growth_data.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "new_users": count
            })
        
        # ==================== RESPONSE ====================
        return {
            "dashboard_type": "super_admin",
            "timestamp": datetime.utcnow().isoformat(),
            
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users,
                "blocked": blocked_users,
                "new_this_month": new_users_this_month,
                "by_type": type_breakdown,
                "growth_last_7_days": growth_data,
                "recent_users": [
                    {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "user_type": user.user_type.value,
                        "is_active": user.is_active,
                        "is_blocked": user.is_blocked,
                        "created_at": user.created_at.isoformat() if user.created_at else None
                    }
                    for user in recent_users
                ]
            },
            
            "revenue": {
                "total_balance_all_wallets": float(total_balance),
                "total_wallets": total_wallets,
                "revenue_this_month": float(revenue_this_month),
                "total_transactions": total_transactions,
                "completed_transactions": completed_transactions,
                "pending_transactions": total_transactions - completed_transactions,
                "currency": "MYR",
                "recent_transactions": [
                    {
                        "id": txn.id,
                        "transaction_id": txn.transaction_id,
                        "user_id": txn.user_id,
                        "amount": float(txn.amount),
                        "type": txn.transaction_type.value,
                        "purpose": txn.purpose.value,
                        "status": txn.status,
                        "created_at": txn.created_at.isoformat() if txn.created_at else None
                    }
                    for txn in recent_transactions
                ]
            },
            
            "activities": {
                "total": total_activities,
                "this_month": activities_this_month,
                "total_cost": float(total_activity_cost)
            },
            
            "support": {
                "total_tickets": total_tickets,
                "open": open_tickets,
                "closed": closed_tickets
            },
            
            "system_health": {
                "status": "healthy",
                "database": "connected",
                "last_updated": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Super admin dashboard error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dashboard: {str(e)}"
        )


# ==========================================================
# ENTERPRISE ADMIN DASHBOARD
# ==========================================================

@router.get("/admin")
async def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enterprise Admin Dashboard - Organization Metrics
    
    Returns:
    - User statistics (limited to individual users)
    - Revenue overview
    - Recent activity
    - Support tickets
    """
    if current_user.user_type.value not in ["enterprise", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # ==================== USER STATISTICS (Individual users only) ====================
        total_users = db.query(User).filter(User.user_type == UserType.INDIVIDUAL).count()
        active_users = db.query(User).filter(
            User.user_type == UserType.INDIVIDUAL,
            User.is_active == True,
            User.is_blocked == False
        ).count()
        blocked_users = db.query(User).filter(
            User.user_type == UserType.INDIVIDUAL,
            User.is_blocked == True
        ).count()
        
        # New users this month
        first_day_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users_this_month = db.query(User).filter(
            User.user_type == UserType.INDIVIDUAL,
            User.created_at >= first_day_of_month
        ).count()
        
        # ==================== WALLET STATISTICS ====================
        total_revenue = db.query(func.sum(Wallet.balance)).scalar() or 0
        total_transactions = db.query(Transaction).count()
        
        completed_transactions = db.query(Transaction).filter(
            Transaction.status == "completed"
        ).count()
        
        # ==================== SUPPORT TICKETS ====================
        try:
            open_tickets = db.query(Ticket).filter(
                Ticket.status.in_(["open", "in_progress"])
            ).count()
            total_tickets = db.query(Ticket).count()
        except Exception:
            open_tickets = 0
            total_tickets = 0
        
        # ==================== RECENT USERS ====================
        recent_users = db.query(User).filter(
            User.user_type == UserType.INDIVIDUAL
        ).order_by(desc(User.created_at)).limit(10).all()
        
        # ==================== RECENT ACTIVITIES ====================
        recent_activities = db.query(UserActivity).order_by(
            desc(UserActivity.created_at)
        ).limit(10).all()
        
        # ==================== RESPONSE ====================
        return {
            "dashboard_type": "admin",
            "timestamp": datetime.utcnow().isoformat(),
            
            "users": {
                "total": total_users,
                "active": active_users,
                "blocked": blocked_users,
                "new_this_month": new_users_this_month,
                "recent_users": [
                    {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "is_active": user.is_active,
                        "is_blocked": user.is_blocked,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "wallet_balance": user.wallet.balance if user.wallet else 0.0
                    }
                    for user in recent_users
                ]
            },
            
            "revenue": {
                "total_balance": float(total_revenue),
                "total_transactions": total_transactions,
                "completed_transactions": completed_transactions,
                "currency": "MYR"
            },
            
            "activities": {
                "recent": [
                    {
                        "id": activity.id,
                        "user_id": activity.user_id,
                        "activity_type": activity.activity_type,
                        "activity_count": activity.activity_count,
                        "cost": float(activity.cost),
                        "created_at": activity.created_at.isoformat() if activity.created_at else None
                    }
                    for activity in recent_activities
                ]
            },
            
            "support": {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Admin dashboard error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dashboard: {str(e)}"
        )


# ==========================================================
# USER DASHBOARD
# ==========================================================

@router.get("/user")
async def get_user_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    User Dashboard - Personal Statistics Only
    
    Returns:
    - Wallet balance
    - Recent transactions
    - Recent activities
    - Support tickets
    - Account info
    """
    try:
        # ==================== WALLET INFO ====================
        wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
        balance = wallet.balance if wallet else 0.0
        
        # ==================== RECENT TRANSACTIONS ====================
        recent_transactions = []
        if wallet:
            recent_transactions = db.query(Transaction).filter(
                Transaction.user_id == current_user.id
            ).order_by(desc(Transaction.created_at)).limit(10).all()
        
        total_transactions = len(recent_transactions)
        
        # Calculate total spent and total credited
        total_spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "DEBIT",
            Transaction.status == "completed"
        ).scalar() or 0
        
        total_credited = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "CREDIT",
            Transaction.status == "completed"
        ).scalar() or 0
        
        # ==================== RECENT ACTIVITIES ====================
        recent_activities = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id
        ).order_by(desc(UserActivity.created_at)).limit(10).all()
        
        total_activities = db.query(UserActivity).filter(
            UserActivity.user_id == current_user.id
        ).count()
        
        total_activity_cost = db.query(func.sum(UserActivity.cost)).filter(
            UserActivity.user_id == current_user.id
        ).scalar() or 0
        
        # ==================== SUPPORT TICKETS ====================
        try:
            total_tickets = db.query(Ticket).filter(
                Ticket.user_id == current_user.id
            ).count()
            
            open_tickets = db.query(Ticket).filter(
                Ticket.user_id == current_user.id,
                Ticket.status.in_(["open", "in_progress"])
            ).count()
            
            recent_tickets = db.query(Ticket).filter(
                Ticket.user_id == current_user.id
            ).order_by(desc(Ticket.created_at)).limit(5).all()
            
        except Exception:
            total_tickets = 0
            open_tickets = 0
            recent_tickets = []
        
        # ==================== RESPONSE ====================
        return {
            "dashboard_type": "user",
            "timestamp": datetime.utcnow().isoformat(),
            
            "profile": {
                "id": current_user.id,
                "full_name": current_user.full_name,
                "email": current_user.email,
                "user_type": current_user.user_type.value,
                "is_active": current_user.is_active,
                "is_blocked": current_user.is_blocked,
                "member_since": current_user.created_at.isoformat() if current_user.created_at else None,
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None
            },
            
            "wallet": {
                "balance": float(balance),
                "total_spent": float(total_spent),
                "total_credited": float(total_credited),
                "currency": "MYR",
                "wallet_created_at": wallet.created_at.isoformat() if wallet and wallet.created_at else None,
                "recent_transactions": [
                    {
                        "id": txn.id,
                        "transaction_id": txn.transaction_id,
                        "amount": float(txn.amount),
                        "type": txn.transaction_type.value,
                        "purpose": txn.purpose.value,
                        "status": txn.status,
                        "description": txn.description,
                        "balance_before": float(txn.balance_before),
                        "balance_after": float(txn.balance_after),
                        "created_at": txn.created_at.isoformat() if txn.created_at else None
                    }
                    for txn in recent_transactions
                ]
            },
            
            "activities": {
                "total": total_activities,
                "total_cost": float(total_activity_cost),
                "recent_activities": [
                    {
                        "id": activity.id,
                        "activity_type": activity.activity_type,
                        "activity_count": activity.activity_count,
                        "cost": float(activity.cost),
                        "created_at": activity.created_at.isoformat() if activity.created_at else None
                    }
                    for activity in recent_activities
                ]
            },
            
            "support": {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "recent_tickets": [
                    {
                        "id": ticket.id,
                        "title": ticket.title,
                        "status": ticket.status,
                        "priority": ticket.priority,
                        "created_at": ticket.created_at.isoformat() if ticket.created_at else None
                    }
                    for ticket in recent_tickets
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ User dashboard error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dashboard: {str(e)}"
        )


# ==========================================================
# GENERAL STATS (Legacy endpoint - kept for compatibility)
# ==========================================================

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics (Legacy endpoint)
    Redirects to appropriate dashboard based on user type
    """
    
    # Redirect to appropriate dashboard
    if current_user.user_type.value == "super_admin":
        return await get_super_admin_dashboard(db=db, current_user=current_user)
    elif current_user.user_type.value == "enterprise":
        return await get_admin_dashboard(db=db, current_user=current_user)
    else:
        return await get_user_dashboard(db=db, current_user=current_user)
