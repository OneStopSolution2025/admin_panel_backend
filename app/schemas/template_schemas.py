from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============= Base Schemas =============
class TemplateBase(BaseModel):
    """Base template schema"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============= Template Schemas =============
class TemplateCreate(TemplateBase):
    template_name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    template_config: Dict[str, Any] = Field(..., description="Template configuration with pages array")
    is_default: bool = False
    
    @validator('template_config')
    def validate_template_config(cls, v):
        if not v:
            raise ValueError('Template configuration is required')
        
        # Must have pages array
        if 'pages' not in v:
            raise ValueError('Template config must contain "pages" array')
        
        if not isinstance(v['pages'], list):
            raise ValueError('Template "pages" must be an array')
        
        if len(v['pages']) < 1:
            raise ValueError('Template must have at least 1 page')
        
        if len(v['pages']) > 1000:
            raise ValueError('Template cannot exceed 1000 pages')
        
        return v


class TemplateUpdate(TemplateBase):
    template_name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    template_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    
    @validator('template_config')
    def validate_template_config(cls, v):
        if v is not None:
            # If provided, must have pages array
            if 'pages' not in v:
                raise ValueError('Template config must contain "pages" array')
            
            if not isinstance(v['pages'], list):
                raise ValueError('Template "pages" must be an array')
            
            if len(v['pages']) < 1:
                raise ValueError('Template must have at least 1 page')
            
            if len(v['pages']) > 1000:
                raise ValueError('Template cannot exceed 1000 pages')
        
        return v


class TemplateResponse(TemplateBase):
    id: int
    user_id: int
    template_name: str
    description: Optional[str]
    total_pages: int
    base_price: float
    extra_page_price: float
    current_price: float
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_used_at: Optional[datetime]
    download_count: Optional[int] = 0


class TemplateDetailResponse(TemplateResponse):
    """Template with full configuration"""
    template_config: Optional[Dict[str, Any]]
    user_name: str
    user_email: str


# ============= Price Calculation Schema =============
class PriceCalculation(TemplateBase):
    total_pages: int
    base_price: float
    extra_page_price: float
    calculated_price: float
    extra_pages: int
    breakdown: str


class PriceQuote(TemplateBase):
    """Price quote for template pages"""
    pages: int = Field(..., ge=1, le=1000)
    

# ============= Download Schemas =============
class TemplateDownloadRequest(TemplateBase):
    template_id: int
    include_metadata: bool = True


class TemplateDownloadResponse(TemplateBase):
    id: int
    download_number: str
    template_id: int
    template_name: str
    pages_at_download: int
    price_charged: float
    file_name: Optional[str]
    file_path: Optional[str]
    downloaded_at: datetime


class TemplateDownloadHistory(TemplateBase):
    """User's download history"""
    id: int
    download_number: str
    template_name: str
    pages_at_download: int
    price_charged: float
    downloaded_at: datetime


# ============= Price History Schemas =============
class PriceHistoryResponse(TemplateBase):
    id: int
    template_id: int
    template_name: str
    old_pages: int
    new_pages: int
    old_price: float
    new_price: float
    change_reason: Optional[str]
    admin_notified: bool
    admin_notified_at: Optional[datetime]
    downloads_before_change: int
    changed_at: datetime


# ============= Settings Schemas =============
class TemplateBuilderSettingsResponse(TemplateBase):
    id: int
    base_price: float
    base_pages_included: int
    extra_page_price: float
    admin_notification_email: Optional[str]
    notify_on_price_change: bool
    notify_on_new_template: bool
    created_at: datetime
    updated_at: Optional[datetime]


class TemplateBuilderSettingsUpdate(TemplateBase):
    base_price: Optional[float] = Field(None, gt=0)
    base_pages_included: Optional[int] = Field(None, ge=1)
    extra_page_price: Optional[float] = Field(None, ge=0)
    admin_notification_email: Optional[str] = None
    notify_on_price_change: Optional[bool] = None
    notify_on_new_template: Optional[bool] = None


# ============= Statistics Schemas =============
class TemplateStatistics(TemplateBase):
    total_templates: int
    active_templates: int
    total_downloads: int
    total_revenue: float
    templates_by_page_range: Dict[str, int]
    average_pages_per_template: float
    most_downloaded_template: Optional[Dict[str, Any]]


class UserTemplateStats(TemplateBase):
    """Statistics for a specific user"""
    total_templates: int
    total_downloads: int
    total_spent: float
    active_templates: int
    default_template: Optional[Dict[str, Any]]


# ============= Notification Schemas =============
class PriceChangeNotification(TemplateBase):
    """Schema for price change notification email"""
    user_id: int
    user_name: str
    user_email: str
    template_id: int
    template_name: str
    old_pages: int
    new_pages: int
    old_price: float
    new_price: float
    downloads_before_change: int
    changed_at: datetime


# ============= Filter Schemas =============
class TemplateFilter(BaseModel):
    user_id: Optional[int] = None
    is_active: Optional[bool] = None
    min_pages: Optional[int] = None
    max_pages: Optional[int] = None
    search: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
