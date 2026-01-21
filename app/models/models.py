from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, Enum as SQLEnum, Text, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from core.database import Base


class UserType(str, enum.Enum):
    """User type enumeration"""
    SUPER_ADMIN = "super_admin"
    ENTERPRISE = "enterprise"
    INDIVIDUAL = "individual"
    SUB_USER = "sub_user"


class TransactionType(str, enum.Enum):
    """Transaction type enumeration"""
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionPurpose(str, enum.Enum):
    """Transaction purpose enumeration"""
    WALLET_TOPUP = "wallet_topup"
    SUBSCRIPTION = "subscription"
    REPORT_GENERATION = "report_generation"
    FORM_DOWNLOAD = "form_download"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    user_type = Column(SQLEnum(UserType), nullable=False)
    
    # Enterprise specific
    enterprise_id = Column(String(50), index=True, nullable=True)
    parent_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="user", cascade="all, delete-orphan")
    # Ticket relationships auto-created via backref in Ticket model: created_tickets, assigned_tickets
    parent = relationship("User", remote_side=[id], backref="sub_users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_type_active', 'user_type', 'is_active'),
        Index('idx_enterprise_parent', 'enterprise_id', 'parent_user_id'),
    )


class Wallet(Base):
    """Wallet model"""
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="wallet")
    
    # Indexes
    __table_args__ = (
        Index('idx_wallet_balance', 'balance'),
    )


class Transaction(Base):
    """Transaction model"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    purpose = Column(SQLEnum(TransactionPurpose), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    # Payment details
    status = Column(String(50), default="pending", nullable=False)  # pending, completed, failed
    payment_method = Column(String(50), nullable=True)  # billplz, manual, etc.
    payment_gateway_id = Column(String(255), nullable=True)  # External payment gateway reference
    
    # Metadata
    description = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)  # JSON data for additional information (avoiding reserved 'metadata' keyword)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_transaction_user_date', 'user_id', 'created_at'),
        Index('idx_transaction_type_purpose', 'transaction_type', 'purpose'),
        Index('idx_transaction_status', 'status'),
    )


class UserActivity(Base):
    """User activity tracking model"""
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Activity details
    activity_type = Column(String(50), nullable=False)  # report_generated, form_downloaded, etc.
    activity_count = Column(Integer, default=1)
    cost = Column(Float, default=0.0)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)  # JSON data for additional information (avoiding reserved 'metadata' keyword)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activities")
    
    # Indexes
    __table_args__ = (
        Index('idx_activity_user_type', 'user_id', 'activity_type'),
        Index('idx_activity_date', 'created_at'),
    )


class RefreshToken(Base):
    """Refresh token model for token rotation"""
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    
    # Token metadata
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    
    # Indexes
    __table_args__ = (
        Index('idx_token_user_revoked', 'user_id', 'is_revoked'),
        Index('idx_token_expires', 'expires_at'),
    )


class SubscriptionPlan(str, enum.Enum):
    """Subscription plan enumeration"""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Invoice(Base):
    """Invoice model for payments"""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Invoice details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="MYR")
    description = Column(Text, nullable=True)
    
    # Payment gateway details
    billplz_bill_id = Column(String(100), unique=True, nullable=True)
    payment_url = Column(Text, nullable=True)
    
    # Status
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="invoices")
    
    # Indexes
    __table_args__ = (
        Index('idx_invoice_user_paid', 'user_id', 'paid'),
        Index('idx_invoice_billplz', 'billplz_bill_id'),
    )


class Subscription(Base):
    """Subscription model"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Subscription details
    plan = Column(SQLEnum(SubscriptionPlan), nullable=False)
    status = Column(String(50), default="active")  # active, cancelled, expired
    
    # Billing
    amount = Column(Float, nullable=False)
    billing_cycle = Column(String(20), default="monthly")  # monthly, yearly
    
    # Dates
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    next_billing_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="subscriptions")
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_user_status', 'user_id', 'status'),
        Index('idx_subscription_plan', 'plan'),
    )
