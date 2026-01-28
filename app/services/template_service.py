from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import uuid
from models.template_models import (
    Template, TemplateDownload, TemplatePriceHistory, TemplateBuilderSettings
)
from models.models import User, Transaction, TransactionPurpose
from schemas.template_schemas import (
    TemplateCreate, TemplateUpdate, TemplateFilter, PriceCalculation
)
from services.wallet_service import WalletService
from core.logging import get_logger
from core.config import settings
from fastapi import HTTPException, status

logger = get_logger(__name__)


class TemplateService:
    """Service for template builder operations with dynamic pricing"""
    
    @staticmethod
    async def get_settings(db: AsyncSession) -> TemplateBuilderSettings:
        """Get or create template builder settings"""
        result = await db.execute(
            select(TemplateBuilderSettings).limit(1)
        )
        settings_obj = result.scalar_one_or_none()
        
        if not settings_obj:
            # Create default settings
            settings_obj = TemplateBuilderSettings(
                base_price=37.0,
                base_pages_included=30,
                extra_page_price=1.0,
                notify_on_price_change=True
            )
            db.add(settings_obj)
            await db.commit()
            await db.refresh(settings_obj)
        
        return settings_obj
    
    @staticmethod
    def calculate_price(total_pages: int, settings: TemplateBuilderSettings) -> PriceCalculation:
        """
        Calculate template price based on pages.
        
        Logic:
        - ≤30 pages: 37RM (base price)
        - >30 pages: 37RM + (extra_pages × 1RM)
        
        Example:
        - 25 pages = 37RM
        - 30 pages = 37RM
        - 35 pages = 37RM + (5 × 1RM) = 42RM
        - 50 pages = 37RM + (20 × 1RM) = 57RM
        """
        base_price = settings.base_price
        base_pages = settings.base_pages_included
        extra_page_price = settings.extra_page_price
        
        if total_pages <= base_pages:
            # Standard price for up to base pages
            calculated_price = base_price
            extra_pages = 0
            breakdown = f"{total_pages} pages ≤ {base_pages} pages: {base_price}RM (standard price)"
        else:
            # Base price + extra pages
            extra_pages = total_pages - base_pages
            calculated_price = base_price + (extra_pages * extra_page_price)
            breakdown = f"{base_price}RM (base) + {extra_pages} extra pages × {extra_page_price}RM = {calculated_price}RM"
        
        return PriceCalculation(
            total_pages=total_pages,
            base_price=base_price,
            extra_page_price=extra_page_price,
            calculated_price=calculated_price,
            extra_pages=extra_pages,
            breakdown=breakdown
        )
    
    @staticmethod
    async def create_template(
        template_data: TemplateCreate,
        user_id: int,
        db: AsyncSession
    ) -> Template:
        """
        Create a new template for user.
        Automatically calculates pages from template_config.pages array.
        Automatically calculates price based on pages.
        """
        # Get pricing settings
        settings_obj = await TemplateService.get_settings(db)
        
        # AUTO-COUNT PAGES from template_config
        if not template_data.template_config or 'pages' not in template_data.template_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template config with pages array is required"
            )
        
        # Count actual pages from config
        total_pages = len(template_data.template_config['pages'])
        
        # Validate page count
        if total_pages < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template must have at least 1 page"
            )
        
        if total_pages > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template cannot exceed 1000 pages"
            )
        
        # Calculate price based on auto-counted pages
        price_calc = TemplateService.calculate_price(
            total_pages,
            settings_obj
        )
        
        # If user wants this as default, unset other defaults
        if template_data.is_default:
            await db.execute(
                select(Template)
                .where(
                    and_(
                        Template.user_id == user_id,
                        Template.is_default == True
                    )
                )
            )
            existing_defaults = (await db.execute(
                select(Template).where(
                    and_(
                        Template.user_id == user_id,
                        Template.is_default == True
                    )
                )
            )).scalars().all()
            
            for template in existing_defaults:
                template.is_default = False
        
        # Create template with AUTO-CALCULATED page count
        template = Template(
            user_id=user_id,
            template_name=template_data.template_name,
            description=template_data.description,
            total_pages=total_pages,  # AUTO-CALCULATED from config
            base_price=price_calc.base_price,
            extra_page_price=price_calc.extra_page_price,
            current_price=price_calc.calculated_price,
            template_config=template_data.template_config,
            is_default=template_data.is_default,
            is_active=True
        )
        
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        logger.info(
            f"Template created: {template.template_name} by user {user_id} "
            f"with {total_pages} pages (auto-counted) at {price_calc.calculated_price}RM"
        )
        
        return template
    
    @staticmethod
    async def update_template(
        template_id: int,
        template_data: TemplateUpdate,
        user_id: int,
        db: AsyncSession
    ) -> Template:
        """
        Update template. If template_config changes (pages added/removed), 
        system auto-recalculates page count and price.
        If pages changed after downloads, notify admin.
        """
        template = await TemplateService.get_template(template_id, db)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check ownership
        if template.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Store old values
        old_pages = template.total_pages
        old_price = template.current_price
        
        # Check if template_config changed (which means pages may have changed)
        pages_changed = False
        new_page_count = old_pages
        
        if template_data.template_config:
            # AUTO-COUNT pages from new config
            if 'pages' not in template_data.template_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Template config must contain pages array"
                )
            
            new_page_count = len(template_data.template_config['pages'])
            
            # Validate
            if new_page_count < 1 or new_page_count > 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Template must have between 1 and 1000 pages"
                )
            
            # Check if page count changed
            if new_page_count != old_pages:
                pages_changed = True
                
                # Check if template has been downloaded
                download_count_result = await db.execute(
                    select(func.count(TemplateDownload.id))
                    .where(TemplateDownload.template_id == template_id)
                )
                download_count = download_count_result.scalar()
                
                # Get settings and recalculate price
                settings_obj = await TemplateService.get_settings(db)
                price_calc = TemplateService.calculate_price(
                    new_page_count,
                    settings_obj
                )
                
                # Update page count and price
                template.total_pages = new_page_count
                template.current_price = price_calc.calculated_price
                
                # If template was already downloaded, record price change and notify admin
                if download_count > 0:
                    await TemplateService._record_price_change(
                        template_id=template_id,
                        user_id=user_id,
                        old_pages=old_pages,
                        new_pages=new_page_count,
                        old_price=old_price,
                        new_price=price_calc.calculated_price,
                        downloads_before_change=download_count,
                        db=db
                    )
                    
                    logger.info(
                        f"AUTO-COUNT PRICE CHANGE: Template {template_id} changed from "
                        f"{old_pages} pages ({old_price}RM) to {new_page_count} "
                        f"pages ({price_calc.calculated_price}RM) after {download_count} downloads. "
                        f"Admin notified!"
                    )
            
            # Update template config
            template.template_config = template_data.template_config
        
        # Update other fields
        if template_data.template_name:
            template.template_name = template_data.template_name
        if template_data.description is not None:
            template.description = template_data.description
        if template_data.is_active is not None:
            template.is_active = template_data.is_active
        if template_data.is_default is not None:
            if template_data.is_default:
                # Unset other defaults
                existing_defaults = (await db.execute(
                    select(Template).where(
                        and_(
                            Template.user_id == user_id,
                            Template.is_default == True,
                            Template.id != template_id
                        )
                    )
                )).scalars().all()
                
                for t in existing_defaults:
                    t.is_default = False
            
            template.is_default = template_data.is_default
        
        template.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(template)
        
        return template
    
    @staticmethod
    async def _record_price_change(
        template_id: int,
        user_id: int,
        old_pages: int,
        new_pages: int,
        old_price: float,
        new_price: float,
        downloads_before_change: int,
        db: AsyncSession
    ):
        """Record price change and mark for admin notification"""
        price_history = TemplatePriceHistory(
            template_id=template_id,
            user_id=user_id,
            old_pages=old_pages,
            new_pages=new_pages,
            old_price=old_price,
            new_price=new_price,
            change_reason="User modified template page count after downloads",
            admin_notified=False,
            downloads_before_change=downloads_before_change
        )
        
        db.add(price_history)
        
        # Trigger notification task (will be implemented in tasks)
        # This will send email to super admin
        logger.warning(
            f"ADMIN NOTIFICATION: Template {template_id} price changed "
            f"after {downloads_before_change} downloads"
        )
    
    @staticmethod
    async def download_template(
        template_id: int,
        user_id: int,
        db: AsyncSession
    ) -> TemplateDownload:
        """
        Download template and charge user based on current template price.
        Deducts amount from wallet.
        """
        template = await TemplateService.get_template(template_id, db)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check ownership
        if template.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if template is active
        if not template.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template is not active"
            )
        
        # Get current price
        price_to_charge = template.current_price
        
        # Check wallet balance
        has_balance = await WalletService.check_sufficient_balance(
            user_id, price_to_charge, db
        )
        
        if not has_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient wallet balance. Required: {price_to_charge}RM"
            )
        
        # Deduct from wallet
        transaction = await WalletService.deduct_funds(
            user_id=user_id,
            amount=price_to_charge,
            purpose=TransactionPurpose.REPORT_GENERATION,  # Using existing purpose
            description=f"Template download: {template.template_name} ({template.total_pages} pages)",
            db=db
        )
        
        # Generate download number
        download_number = f"DL-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create download record
        download = TemplateDownload(
            download_number=download_number,
            template_id=template_id,
            user_id=user_id,
            pages_at_download=template.total_pages,
            price_charged=price_to_charge,
            transaction_id=transaction.id,
            file_name=f"{template.template_name.replace(' ', '_')}.pdf",
            file_path=f"/downloads/{user_id}/{download_number}.pdf"
        )
        
        db.add(download)
        
        # Update template last used
        template.last_used_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(download)
        
        logger.info(
            f"Template downloaded: {template.template_name} by user {user_id} "
            f"charged {price_to_charge}RM"
        )
        
        return download
    
    @staticmethod
    async def get_template(template_id: int, db: AsyncSession) -> Optional[Template]:
        """Get template by ID"""
        result = await db.execute(
            select(Template).where(Template.id == template_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_templates(
        user_id: int,
        skip: int,
        limit: int,
        is_active: Optional[bool],
        db: AsyncSession
    ) -> Tuple[List[Template], int]:
        """Get user's templates with pagination"""
        query = select(Template).where(Template.user_id == user_id)
        
        if is_active is not None:
            query = query.where(Template.is_active == is_active)
        
        # Get total count
        count_result = await db.execute(
            select(func.count(Template.id)).where(Template.user_id == user_id)
        )
        total = count_result.scalar()
        
        # Get templates
        query = query.order_by(desc(Template.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        templates = result.scalars().all()
        
        return list(templates), total
    
    @staticmethod
    async def get_download_history(
        user_id: int,
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> Tuple[List[TemplateDownload], int]:
        """Get user's download history"""
        # Get total count
        count_result = await db.execute(
            select(func.count(TemplateDownload.id))
            .where(TemplateDownload.user_id == user_id)
        )
        total = count_result.scalar()
        
        # Get downloads
        result = await db.execute(
            select(TemplateDownload)
            .where(TemplateDownload.user_id == user_id)
            .order_by(desc(TemplateDownload.downloaded_at))
            .offset(skip)
            .limit(limit)
        )
        downloads = result.scalars().all()
        
        return list(downloads), total
    
    @staticmethod
    async def get_price_changes_for_admin(
        skip: int,
        limit: int,
        unnotified_only: bool,
        db: AsyncSession
    ) -> Tuple[List[TemplatePriceHistory], int]:
        """Get price change history for admin review"""
        query = select(TemplatePriceHistory)
        
        if unnotified_only:
            query = query.where(TemplatePriceHistory.admin_notified == False)
        
        # Get total count
        count_query = select(func.count(TemplatePriceHistory.id))
        if unnotified_only:
            count_query = count_query.where(TemplatePriceHistory.admin_notified == False)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get history
        query = query.order_by(desc(TemplatePriceHistory.changed_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        history = result.scalars().all()
        
        return list(history), total
    
    @staticmethod
    async def mark_price_change_notified(
        history_id: int,
        db: AsyncSession
    ):
        """Mark price change as notified to admin"""
        result = await db.execute(
            select(TemplatePriceHistory).where(TemplatePriceHistory.id == history_id)
        )
        history = result.scalar_one_or_none()
        
        if history:
            history.admin_notified = True
            history.admin_notified_at = datetime.utcnow()
            history.notification_email_sent = True
            await db.commit()
