from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from api.deps import get_current_active_user
from models.models import User
from models.template_models import Template

router = APIRouter()

@router.get("/")
async def get_templates(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all active templates"""
    templates = db.query(Template)\
        .filter(Template.is_active == True)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return templates

@router.post("/")
async def create_template(
    name: str,
    description: str = None,
    base_price: float = 37.0,
    price_per_page: float = 1.0,
    content: dict = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    template = Template(
        name=name,
        description=description,
        base_price=base_price,
        price_per_page=price_per_page,
        content=content
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {
        "message": "Template created",
        "template_id": template.id,
        "template": template
    }

@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Get template by ID"""
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return template

@router.put("/{template_id}")
async def update_template(
    template_id: int,
    name: str = None,
    description: str = None,
    base_price: float = None,
    price_per_page: float = None,
    is_active: bool = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if base_price is not None:
        template.base_price = base_price
    if price_per_page is not None:
        template.price_per_page = price_per_page
    if is_active is not None:
        template.is_active = is_active
    
    db.commit()
    db.refresh(template)
    
    return {
        "message": "Template updated",
        "template": template
    }

@router.post("/{template_id}/calculate-price")
async def calculate_price(
    template_id: int,
    num_pages: int,
    db: Session = Depends(get_db)
):
    """Calculate price for template based on number of pages"""
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    if num_pages < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of pages must be at least 1"
        )
    
    # Calculate: base_price + (num_pages * price_per_page)
    total_price = template.base_price + (num_pages * template.price_per_page)
    
    return {
        "template_id": template_id,
        "template_name": template.name,
        "num_pages": num_pages,
        "base_price": template.base_price,
        "price_per_page": template.price_per_page,
        "total_price": total_price
    }
