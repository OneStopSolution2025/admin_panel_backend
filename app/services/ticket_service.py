from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import uuid
from models.ticket_models import (
    Ticket, TicketComment, TicketAttachment, TicketStatusHistory,
    TicketSLAConfig, TicketStatus, TicketPriority, TicketCategory
)
from models.models import User
from schemas.ticket_schemas import (
    TicketCreate, TicketUpdate, TicketCommentCreate,
    TicketFilter, TicketAssignmentRequest, TicketStatusChangeRequest
)
from core.logging import get_logger
from fastapi import HTTPException, status

logger = get_logger(__name__)


class TicketService:
    """Service for ticket management operations"""
    
    @staticmethod
    async def create_ticket(
        ticket_data: TicketCreate,
        user_id: int,
        db: AsyncSession
    ) -> Ticket:
        """
        Create a new support ticket.
        Automatically generates unique ticket number.
        """
        # Generate unique ticket number
        ticket_number = await TicketService._generate_ticket_number(db)
        
        # Create ticket
        ticket = Ticket(
            ticket_number=ticket_number,
            user_id=user_id,
            subject=ticket_data.subject,
            description=ticket_data.description,
            priority=ticket_data.priority,
            category=ticket_data.category,
            status=TicketStatus.OPEN,
            tags=ticket_data.tags
        )
        
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        
        logger.info(f"Ticket created: {ticket_number} by user {user_id}")
        return ticket
    
    @staticmethod
    async def _generate_ticket_number(db: AsyncSession) -> str:
        """Generate unique ticket number in format TKT-YYYYMMDD-XXXX"""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        
        # Get count of tickets created today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.created_at >= today_start)
        )
        count = result.scalar() or 0
        
        return f"TKT-{date_str}-{(count + 1):04d}"
    
    @staticmethod
    async def get_ticket(
        ticket_id: int,
        db: AsyncSession
    ) -> Optional[Ticket]:
        """Get ticket by ID"""
        result = await db.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_ticket_by_number(
        ticket_number: str,
        db: AsyncSession
    ) -> Optional[Ticket]:
        """Get ticket by ticket number"""
        result = await db.execute(
            select(Ticket).where(Ticket.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_ticket(
        ticket_id: int,
        ticket_data: TicketUpdate,
        user_id: int,
        db: AsyncSession
    ) -> Ticket:
        """
        Update ticket details.
        Records status changes in history.
        """
        ticket = await TicketService.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Store old values for history
        old_status = ticket.status
        old_priority = ticket.priority
        old_assigned_to = ticket.assigned_to_id
        
        # Update fields
        update_data = ticket_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ticket, field, value)
        
        ticket.updated_at = datetime.utcnow()
        
        # Record status change if status changed
        if 'status' in update_data or 'priority' in update_data or 'assigned_to_id' in update_data:
            await TicketService._record_status_change(
                ticket_id=ticket_id,
                changed_by_id=user_id,
                from_status=old_status,
                to_status=ticket.status,
                from_priority=old_priority,
                to_priority=ticket.priority,
                from_assigned_to_id=old_assigned_to,
                to_assigned_to_id=ticket.assigned_to_id,
                db=db
            )
        
        # Update timestamps based on status
        if ticket.status == TicketStatus.RESOLVED and not ticket.resolved_at:
            ticket.resolved_at = datetime.utcnow()
        elif ticket.status == TicketStatus.CLOSED and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(ticket)
        
        logger.info(f"Ticket {ticket.ticket_number} updated by user {user_id}")
        return ticket
    
    @staticmethod
    async def assign_ticket(
        ticket_id: int,
        assignment_data: TicketAssignmentRequest,
        assigned_by_id: int,
        db: AsyncSession
    ) -> Ticket:
        """Assign ticket to support staff"""
        ticket = await TicketService.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        old_assigned_to = ticket.assigned_to_id
        ticket.assigned_to_id = assignment_data.assigned_to_id
        ticket.updated_at = datetime.utcnow()
        
        # If ticket was open, move to in_progress
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
        
        # Record change
        await TicketService._record_status_change(
            ticket_id=ticket_id,
            changed_by_id=assigned_by_id,
            from_status=ticket.status,
            to_status=ticket.status,
            from_assigned_to_id=old_assigned_to,
            to_assigned_to_id=assignment_data.assigned_to_id,
            change_note=assignment_data.note,
            db=db
        )
        
        await db.commit()
        await db.refresh(ticket)
        
        logger.info(f"Ticket {ticket.ticket_number} assigned to user {assignment_data.assigned_to_id}")
        return ticket
    
    @staticmethod
    async def change_status(
        ticket_id: int,
        status_data: TicketStatusChangeRequest,
        user_id: int,
        db: AsyncSession
    ) -> Ticket:
        """Change ticket status"""
        ticket = await TicketService.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        old_status = ticket.status
        ticket.status = status_data.status
        ticket.updated_at = datetime.utcnow()
        
        # Update timestamps
        if status_data.status == TicketStatus.RESOLVED and not ticket.resolved_at:
            ticket.resolved_at = datetime.utcnow()
        elif status_data.status == TicketStatus.CLOSED and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
        
        # Record change
        await TicketService._record_status_change(
            ticket_id=ticket_id,
            changed_by_id=user_id,
            from_status=old_status,
            to_status=status_data.status,
            change_note=status_data.note,
            db=db
        )
        
        # If this is a resolution, add comment
        if status_data.is_resolution and status_data.note:
            await TicketService.add_comment(
                ticket_id=ticket_id,
                user_id=user_id,
                comment_data=TicketCommentCreate(
                    comment=status_data.note,
                    is_resolution=True
                ),
                db=db
            )
        
        await db.commit()
        await db.refresh(ticket)
        
        logger.info(f"Ticket {ticket.ticket_number} status changed to {status_data.status}")
        return ticket
    
    @staticmethod
    async def _record_status_change(
        ticket_id: int,
        changed_by_id: int,
        from_status: Optional[TicketStatus],
        to_status: TicketStatus,
        from_priority: Optional[TicketPriority] = None,
        to_priority: Optional[TicketPriority] = None,
        from_assigned_to_id: Optional[int] = None,
        to_assigned_to_id: Optional[int] = None,
        change_note: Optional[str] = None,
        db: AsyncSession = None
    ):
        """Record ticket status change in history"""
        history = TicketStatusHistory(
            ticket_id=ticket_id,
            changed_by_id=changed_by_id,
            from_status=from_status,
            to_status=to_status,
            from_priority=from_priority,
            to_priority=to_priority,
            from_assigned_to_id=from_assigned_to_id,
            to_assigned_to_id=to_assigned_to_id,
            change_note=change_note
        )
        db.add(history)
    
    @staticmethod
    async def add_comment(
        ticket_id: int,
        user_id: int,
        comment_data: TicketCommentCreate,
        db: AsyncSession
    ) -> TicketComment:
        """Add comment to ticket"""
        # Verify ticket exists
        ticket = await TicketService.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Create comment
        comment = TicketComment(
            ticket_id=ticket_id,
            user_id=user_id,
            comment=comment_data.comment,
            is_internal=comment_data.is_internal,
            is_resolution=comment_data.is_resolution
        )
        
        db.add(comment)
        
        # Update ticket's first_response_at if this is first staff response
        if not ticket.first_response_at and not comment.is_internal:
            # Check if commenter is staff (not the ticket creator)
            if user_id != ticket.user_id:
                ticket.first_response_at = datetime.utcnow()
        
        ticket.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(comment)
        
        logger.info(f"Comment added to ticket {ticket.ticket_number}")
        return comment
    
    @staticmethod
    async def get_tickets(
        filters: TicketFilter,
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> Tuple[List[Ticket], int]:
        """Get tickets with filters and pagination"""
        # Build query
        query = select(Ticket)
        conditions = []
        
        if filters.status:
            conditions.append(Ticket.status == filters.status)
        if filters.priority:
            conditions.append(Ticket.priority == filters.priority)
        if filters.category:
            conditions.append(Ticket.category == filters.category)
        if filters.assigned_to_id:
            conditions.append(Ticket.assigned_to_id == filters.assigned_to_id)
        if filters.user_id:
            conditions.append(Ticket.user_id == filters.user_id)
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    Ticket.subject.ilike(search_term),
                    Ticket.description.ilike(search_term),
                    Ticket.ticket_number.ilike(search_term)
                )
            )
        if filters.start_date:
            conditions.append(Ticket.created_at >= filters.start_date)
        if filters.end_date:
            conditions.append(Ticket.created_at <= filters.end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count(Ticket.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get tickets
        query = query.order_by(desc(Ticket.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        tickets = result.scalars().all()
        
        return list(tickets), total
    
    @staticmethod
    async def get_ticket_statistics(
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        db: AsyncSession
    ) -> Dict:
        """Get ticket statistics"""
        # Build base query
        query = select(Ticket)
        if start_date:
            query = query.where(Ticket.created_at >= start_date)
        if end_date:
            query = query.where(Ticket.created_at <= end_date)
        
        result = await db.execute(query)
        tickets = result.scalars().all()
        
        # Calculate statistics
        total_tickets = len(tickets)
        open_tickets = sum(1 for t in tickets if t.status == TicketStatus.OPEN)
        in_progress = sum(1 for t in tickets if t.status == TicketStatus.IN_PROGRESS)
        resolved = sum(1 for t in tickets if t.status == TicketStatus.RESOLVED)
        closed = sum(1 for t in tickets if t.status == TicketStatus.CLOSED)
        
        # By priority
        tickets_by_priority = {
            priority.value: sum(1 for t in tickets if t.priority == priority)
            for priority in TicketPriority
        }
        
        # By category
        tickets_by_category = {
            category.value: sum(1 for t in tickets if t.category == category)
            for category in TicketCategory
        }
        
        # Average resolution time
        resolved_tickets = [t for t in tickets if t.resolved_at and t.created_at]
        if resolved_tickets:
            avg_resolution = sum(
                (t.resolved_at - t.created_at).total_seconds()
                for t in resolved_tickets
            ) / len(resolved_tickets)
            avg_resolution_hours = avg_resolution / 3600
        else:
            avg_resolution_hours = None
        
        # Average first response time
        responded_tickets = [t for t in tickets if t.first_response_at and t.created_at]
        if responded_tickets:
            avg_response = sum(
                (t.first_response_at - t.created_at).total_seconds()
                for t in responded_tickets
            ) / len(responded_tickets)
            avg_response_hours = avg_response / 3600
        else:
            avg_response_hours = None
        
        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "in_progress_tickets": in_progress,
            "resolved_tickets": resolved,
            "closed_tickets": closed,
            "tickets_by_priority": tickets_by_priority,
            "tickets_by_category": tickets_by_category,
            "average_resolution_time": avg_resolution_hours,
            "average_first_response_time": avg_response_hours
        }
