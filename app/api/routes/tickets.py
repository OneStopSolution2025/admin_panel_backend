from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from api.deps import get_current_active_user
from models.models import User
from models.ticket_models import Ticket, TicketStatus

router = APIRouter()

@router.get("/")
async def get_tickets(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user tickets"""
    tickets = db.query(Ticket)\
        .filter(Ticket.user_id == current_user.id)\
        .order_by(Ticket.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return tickets

@router.post("/")
async def create_ticket(
    title: str,
    description: str,
    priority: str = "medium",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new ticket"""
    ticket = Ticket(
        user_id=current_user.id,
        title=title,
        description=description,
        priority=priority,
        status=TicketStatus.OPEN
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    return {
        "message": "Ticket created successfully",
        "ticket_id": ticket.id,
        "ticket": ticket
    }

@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get ticket by ID"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check if user owns ticket or is admin
    if ticket.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this ticket"
        )
    
    return ticket

@router.put("/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    status: str = None,
    priority: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if ticket.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this ticket"
        )
    
    if status:
        ticket.status = status
    if priority:
        ticket.priority = priority
    
    db.commit()
    db.refresh(ticket)
    
    return {
        "message": "Ticket updated",
        "ticket": ticket
    }
