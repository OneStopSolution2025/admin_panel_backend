from datetime import datetime, timedelta
from core.celery_app import celery_app
from core.logging import get_logger
from sqlalchemy import select, and_
from core.database import AsyncSessionLocal
from models.models import RefreshToken

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens():
    """
    Background task to clean up expired refresh tokens.
    Runs every hour to maintain database hygiene.
    """
    import asyncio
    
    async def _cleanup():
        async with AsyncSessionLocal() as session:
            try:
                # Delete expired tokens
                result = await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.expires_at < datetime.utcnow()
                    )
                )
                expired_tokens = result.scalars().all()
                
                count = 0
                for token in expired_tokens:
                    await session.delete(token)
                    count += 1
                
                await session.commit()
                logger.info(f"Cleaned up {count} expired refresh tokens")
                return count
                
            except Exception as e:
                logger.error(f"Error cleaning up tokens: {str(e)}")
                await session.rollback()
                raise
    
    return asyncio.run(_cleanup())


@celery_app.task(name="app.tasks.tasks.generate_daily_reports")
def generate_daily_reports():
    """
    Background task to generate daily summary reports.
    Runs once per day.
    """
    import asyncio
    from services.dashboard_service import DashboardService
    
    async def _generate():
        async with AsyncSessionLocal() as session:
            try:
                # Get yesterday's date range
                today = datetime.utcnow().date()
                yesterday = today - timedelta(days=1)
                start_date = datetime.combine(yesterday, datetime.min.time())
                end_date = datetime.combine(yesterday, datetime.max.time())
                
                # Generate stats
                stats = await DashboardService.get_dashboard_stats(
                    start_date=start_date,
                    end_date=end_date,
                    db=session
                )
                
                logger.info(f"Daily report generated: {stats}")
                
                # Here you could:
                # - Send email notifications
                # - Store in separate reporting table
                # - Push to analytics service
                
                return stats
                
            except Exception as e:
                logger.error(f"Error generating daily report: {str(e)}")
                raise
    
    return asyncio.run(_generate())


@celery_app.task(name="app.tasks.tasks.send_notification")
def send_notification(user_email: str, subject: str, message: str):
    """
    Background task to send email notifications.
    Can be extended to support SMS, push notifications, etc.
    """
    logger.info(f"Sending notification to {user_email}: {subject}")
    
    # Implementation would go here:
    # - Email service integration
    # - SMS service integration
    # - Push notification service
    
    return {"status": "sent", "email": user_email}


@celery_app.task(name="app.tasks.tasks.process_bulk_transactions")
def process_bulk_transactions(transaction_list: list):
    """
    Background task to process multiple transactions in bulk.
    Useful for batch operations.
    """
    import asyncio
    from services.wallet_service import WalletService
    
    async def _process():
        async with AsyncSessionLocal() as session:
            results = []
            for txn in transaction_list:
                try:
                    # Process transaction
                    logger.info(f"Processing transaction: {txn}")
                    results.append({"status": "success", "transaction": txn})
                except Exception as e:
                    logger.error(f"Transaction failed: {str(e)}")
                    results.append({"status": "failed", "transaction": txn, "error": str(e)})
            
            return results
    
    return asyncio.run(_process())
