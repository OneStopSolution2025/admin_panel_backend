from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    ForeignKey, Enum as SQLEnum, Boolean, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from core.database import Base


class TicketStatus(str, enum.Enum):
    """Ticket status enumeration"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class TicketPriority(str, enum.Enum):
    """Ticket priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, enum.Enum):
    """Ticket category enumeration"""
    TECHNICAL_SUPPORT = "technical_support"
    BILLING = "billing"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL_INQUIRY = "general_inquiry"
    OTHER = "other"


class Ticket(Base):
    """Ticket model for support ticket system"""
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, index=True, nullable=False)
    
    # User who created the ticket
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Assigned support staff (can be null if unassigned)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Ticket details
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(SQLEnum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    category = Column(SQLEnum(TicketCategory), default=TicketCategory.GENERAL_INQUIRY, nullable=False)
    
    # SLA tracking
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    is_internal = Column(Boolean, default=False)  # Internal tickets (staff only)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[user_id], backref="created_tickets")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], backref="assigned_tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_ticket_status_priority', 'status', 'priority'),
        Index('idx_ticket_user_status', 'user_id', 'status'),
        Index('idx_ticket_assigned_status', 'assigned_to_id', 'status'),
        Index('idx_ticket_created_at', 'created_at'),
        Index('idx_ticket_category', 'category'),
    )


class TicketComment(Base):
    """Comments/replies on tickets"""
    __tablename__ = "ticket_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Comment details
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # Internal notes visible only to staff
    is_resolution = Column(Boolean, default=False)  # Marks this comment as the resolution
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User", backref="ticket_comments")
    
    # Indexes
    __table_args__ = (
        Index('idx_comment_ticket_created', 'ticket_id', 'created_at'),
        Index('idx_comment_user', 'user_id'),
    )


class TicketAttachment(Base):
    """File attachments for tickets"""
    __tablename__ = "ticket_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_id = Column(Integer, ForeignKey("ticket_comments.id"), nullable=True)
    
    # File details
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(100), nullable=False)  # MIME type
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")
    uploaded_by = relationship("User", backref="ticket_attachments")
    
    # Indexes
    __table_args__ = (
        Index('idx_attachment_ticket', 'ticket_id'),
        Index('idx_attachment_user', 'uploaded_by_id'),
    )


class TicketStatusHistory(Base):
    """Track ticket status changes for audit trail"""
    __tablename__ = "ticket_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Status change details
    from_status = Column(SQLEnum(TicketStatus), nullable=True)
    to_status = Column(SQLEnum(TicketStatus), nullable=False)
    from_priority = Column(SQLEnum(TicketPriority), nullable=True)
    to_priority = Column(SQLEnum(TicketPriority), nullable=True)
    from_assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Comment about the change
    change_note = Column(Text, nullable=True)
    
    # Timestamp
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    changed_by = relationship("User", foreign_keys=[changed_by_id])
    from_assigned = relationship("User", foreign_keys=[from_assigned_to_id])
    to_assigned = relationship("User", foreign_keys=[to_assigned_to_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_history_ticket', 'ticket_id'),
        Index('idx_history_changed_at', 'changed_at'),
    )


class TicketSLAConfig(Base):
    """SLA configuration for different ticket priorities"""
    __tablename__ = "ticket_sla_config"
    
    id = Column(Integer, primary_key=True, index=True)
    priority = Column(SQLEnum(TicketPriority), unique=True, nullable=False)
    
    # SLA times in minutes
    first_response_time = Column(Integer, nullable=False)  # Minutes to first response
    resolution_time = Column(Integer, nullable=False)  # Minutes to resolution
    
    # Business hours
    applies_business_hours_only = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
