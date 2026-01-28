from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from api.deps import get_current_active_user
from models.models import User, Wallet

router = APIRouter()

@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user wallet balance"""
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        # Create wallet if doesn't exist
        wallet = Wallet(user_id=current_user.id, balance=0.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    return {
        "user_id": current_user.id,
        "balance": wallet.balance,
        "updated_at": wallet.updated_at
    }

@router.post("/deposit")
async def deposit(
    amount: float,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deposit funds to wallet"""
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=0.0)
        db.add(wallet)
    
    wallet.balance += amount
    db.commit()
    db.refresh(wallet)
    
    return {
        "message": "Deposit successful",
        "new_balance": wallet.balance
    }

@router.post("/withdraw")
async def withdraw(
    amount: float,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Withdraw funds from wallet"""
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet or wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )
    
    wallet.balance -= amount
    db.commit()
    db.refresh(wallet)
    
    return {
        "message": "Withdrawal successful",
        "new_balance": wallet.balance
    }
