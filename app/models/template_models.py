"""
Template Models - Complete with all classes
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from core.database import Base


class TemplateFieldType(enum.Enum):
    """Field types for template"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    IMAGE = "image"
    SIGNATURE = "signature"


class Template(Base):
    """
    Template Model
    Stores report templates for users
    """
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Template details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    
    # Template structure (JSON)
    structure = Column(JSON, nullable=False)  # Stores field definitions
    
    # Settings
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # Can other users see/use it?
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="templates")
    fields = relationship("TemplateField", back_populates="template", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Template(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class TemplateField(Base):
    """
    Template Field Model
    Individual fields within a template
    """
    __tablename__ = "template_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    
    # Field details
    field_name = Column(String(255), nullable=False)
    field_type = Column(SQLEnum(TemplateFieldType), nullable=False)
    label = Column(String(255), nullable=False)
    
    # Field configuration
    placeholder = Column(String(255), nullable=True)
    default_value = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)  # For dropdown, checkbox options
    
    # Validation
    is_required = Column(Boolean, default=False)
    min_value = Column(Integer, nullable=True)
    max_value = Column(Integer, nullable=True)
    min_length = Column(Integer, nullable=True)
    max_length = Column(Integer, nullable=True)
    
    # Display order
    order = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    template = relationship("Template", back_populates="fields")
    
    def __repr__(self):
        return f"<TemplateField(id={self.id}, name='{self.field_name}', type={self.field_type.value})>"
