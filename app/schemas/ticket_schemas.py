from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from models.ticket_models import TicketStatus, TicketPriority, TicketCategory


# ============= Base Schemas =============
class TicketBase(BaseModel):
    """Base ticket schema"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============= Ticket Schemas =============
class TicketCreate(TicketBase):
    subject: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.GENERAL_INQUIRY
    tags: Optional[str] = None


class TicketUpdate(TicketBase):
    subject: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assigned_to_id: Optional[int] = None
    tags: Optional[str] = None


class TicketResponse(TicketBase):
    id: int
    ticket_number: str
    user_id: int
    assigned_to_id: Optional[int]
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    tags: Optional[str]
    is_internal: bool
    first_response_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class TicketDetailResponse(TicketResponse):
    """Ticket with creator and assignee details"""
    creator_name: str
    creator_email: str
    assigned_to_name: Optional[str]
    assigned_to_email: Optional[str]
    comments_count: int
    attachments_count: int


class TicketListResponse(TicketBase):
    """Simplified ticket for list views"""
    id: int
    ticket_number: str
    subject: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    creator_name: str
    assigned_to_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


# ============= Comment Schemas =============
class TicketCommentCreate(TicketBase):
    comment: str = Field(..., min_length=1)
    is_internal: bool = False
    is_resolution: bool = False


class TicketCommentUpdate(TicketBase):
    comment: str = Field(..., min_length=1)


class TicketCommentResponse(TicketBase):
    id: int
    ticket_id: int
    user_id: int
    comment: str
    is_internal: bool
    is_resolution: bool
    created_at: datetime
    updated_at: Optional[datetime]
    author_name: str
    author_email: str


# ============= Attachment Schemas =============
class TicketAttachmentResponse(TicketBase):
    id: int
    ticket_id: int
    uploaded_by_id: int
    comment_id: Optional[int]
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    created_at: datetime
    uploaded_by_name: str


# ============= Status History Schemas =============
class TicketStatusHistoryResponse(TicketBase):
    id: int
    ticket_id: int
    changed_by_id: int
    from_status: Optional[TicketStatus]
    to_status: TicketStatus
    from_priority: Optional[TicketPriority]
    to_priority: Optional[TicketPriority]
    from_assigned_to_id: Optional[int]
    to_assigned_to_id: Optional[int]
    change_note: Optional[str]
    changed_at: datetime
    changed_by_name: str


# ============= SLA Config Schemas =============
class SLAConfigCreate(TicketBase):
    priority: TicketPriority
    first_response_time: int = Field(..., gt=0, description="Minutes to first response")
    resolution_time: int = Field(..., gt=0, description="Minutes to resolution")
    applies_business_hours_only: bool = True


class SLAConfigUpdate(TicketBase):
    first_response_time: Optional[int] = Field(None, gt=0)
    resolution_time: Optional[int] = Field(None, gt=0)
    applies_business_hours_only: Optional[bool] = None


class SLAConfigResponse(TicketBase):
    id: int
    priority: TicketPriority
    first_response_time: int
    resolution_time: int
    applies_business_hours_only: bool
    created_at: datetime
    updated_at: Optional[datetime]


# ============= Filter Schemas =============
class TicketFilter(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assigned_to_id: Optional[int] = None
    user_id: Optional[int] = None
    search: Optional[str] = None  # Search in subject/description
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_overdue: Optional[bool] = None


# ============= Statistics Schemas =============
class TicketStatistics(TicketBase):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    tickets_by_priority: dict
    tickets_by_category: dict
    average_resolution_time: Optional[float]  # in hours
    average_first_response_time: Optional[float]  # in hours
    sla_compliance_rate: Optional[float]  # percentage


class TicketAssignmentRequest(TicketBase):
    assigned_to_id: int
    note: Optional[str] = None


class TicketStatusChangeRequest(TicketBase):
    status: TicketStatus
    note: Optional[str] = None
    is_resolution: bool = False


class BulkTicketOperation(TicketBase):
    ticket_ids: List[int] = Field(..., min_items=1)
    operation: str = Field(..., pattern="^(assign|close|change_priority|change_status)$")
    assigned_to_id: Optional[int] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    note: Optional[str] = None
