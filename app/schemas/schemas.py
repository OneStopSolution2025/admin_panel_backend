from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from models.models import UserType, TransactionType, TransactionPurpose


# ============= Base Schemas =============
class BaseSchema(BaseModel):
    """Base schema with common config"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============= User Schemas =============
class UserBase(BaseSchema):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    user_type: UserType
    enterprise_id: Optional[str] = None
    parent_user_id: Optional[int] = None
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    is_active: Optional[bool] = None
    is_blocked: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    user_type: UserType
    enterprise_id: Optional[str]
    parent_user_id: Optional[int]
    is_active: bool
    is_blocked: bool
    created_at: datetime
    last_login: Optional[datetime]


class UserWithWallet(UserResponse):
    wallet_balance: float


# ============= Wallet Schemas =============
class WalletResponse(BaseSchema):
    id: int
    user_id: int
    balance: float
    created_at: datetime
    updated_at: Optional[datetime]


class WalletTopup(BaseSchema):
    amount: float = Field(..., gt=0, description="Amount to add to wallet")


# ============= Transaction Schemas =============
class TransactionResponse(BaseSchema):
    id: int
    transaction_id: str
    user_id: int
    transaction_type: TransactionType
    purpose: TransactionPurpose
    amount: float
    balance_before: float
    balance_after: float
    description: Optional[str]
    created_at: datetime


class TransactionCreate(BaseSchema):
    user_id: int
    transaction_type: TransactionType
    purpose: TransactionPurpose
    amount: float
    description: Optional[str] = None


# ============= Activity Schemas =============
class ActivityResponse(BaseSchema):
    id: int
    user_id: int
    activity_type: str
    activity_count: int
    cost: float
    created_at: datetime


class ActivityCreate(BaseSchema):
    user_id: int
    activity_type: str
    cost: float
    meta_data: Optional[str] = None


# ============= Authentication Schemas =============
class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseSchema):
    refresh_token: str


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class PasswordChange(BaseSchema):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


# ============= Dashboard Schemas =============
class DashboardStats(BaseSchema):
    total_users: int
    total_enterprise_users: int
    total_individual_users: int
    total_sub_users: int
    total_reports_generated: int
    total_forms_downloaded: int
    total_revenue: float
    total_tickets: int = 0
    open_tickets: int = 0
    resolved_tickets: int = 0


class EnterpriseUserSummary(BaseSchema):
    id: int
    enterprise_id: str
    full_name: str
    email: str
    sub_user_count: int
    reports_generated: int
    forms_downloaded: int
    wallet_balance: float
    is_active: bool


class RevenueStats(BaseSchema):
    period: str
    revenue: float
    transaction_count: int


# ============= Pagination Schemas =============
class PaginationParams(BaseSchema):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema):
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int


# ============= Filter Schemas =============
class DateFilter(BaseSchema):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class UserFilter(DateFilter):
    user_type: Optional[UserType] = None
    is_active: Optional[bool] = None
    is_blocked: Optional[bool] = None
    enterprise_id: Optional[str] = None


class TransactionFilter(DateFilter):
    transaction_type: Optional[TransactionType] = None
    purpose: Optional[TransactionPurpose] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None


# ============= Sub-user Schemas =============
class SubUserCreate(UserCreate):
    enterprise_id: str = Field(..., description="Parent enterprise ID")
    

class SubUserResponse(UserResponse):
    parent_enterprise_id: str
    parent_user_name: str
