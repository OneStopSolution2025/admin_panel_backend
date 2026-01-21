from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime
import uuid
from models.models import Wallet, Transaction, User, TransactionType, TransactionPurpose
from schemas.schemas import TransactionResponse, WalletResponse
from core.config import settings
from core.logging import get_logger
from fastapi import HTTPException, status

logger = get_logger(__name__)


class WalletService:
    """Service for wallet operations and transaction management"""
    
    @staticmethod
    async def get_wallet(user_id: int, db: AsyncSession) -> Optional[Wallet]:
        """Get user's wallet"""
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_wallet(user_id: int, db: AsyncSession) -> Wallet:
        """Create a new wallet for user"""
        wallet = Wallet(user_id=user_id, balance=0.0)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        logger.info(f"Wallet created for user_id: {user_id}")
        return wallet
    
    @staticmethod
    async def get_or_create_wallet(user_id: int, db: AsyncSession) -> Wallet:
        """Get existing wallet or create new one"""
        wallet = await WalletService.get_wallet(user_id, db)
        if not wallet:
            wallet = await WalletService.create_wallet(user_id, db)
        return wallet
    
    @staticmethod
    async def add_funds(
        user_id: int,
        amount: float,
        description: Optional[str],
        db: AsyncSession
    ) -> Transaction:
        """
        Add funds to user's wallet.
        Creates a credit transaction and updates wallet balance.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero"
            )
        
        # Get or create wallet
        wallet = await WalletService.get_or_create_wallet(user_id, db)
        
        # Create transaction
        transaction = await WalletService._create_transaction(
            user_id=user_id,
            transaction_type=TransactionType.CREDIT,
            purpose=TransactionPurpose.WALLET_TOPUP,
            amount=amount,
            balance_before=wallet.balance,
            description=description,
            db=db
        )
        
        # Update wallet balance
        wallet.balance += amount
        wallet.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(transaction)
        
        logger.info(f"Added {amount} to user_id {user_id}. New balance: {wallet.balance}")
        return transaction
    
    @staticmethod
    async def deduct_funds(
        user_id: int,
        amount: float,
        purpose: TransactionPurpose,
        description: Optional[str],
        db: AsyncSession
    ) -> Transaction:
        """
        Deduct funds from user's wallet.
        Creates a debit transaction and updates wallet balance.
        Raises exception if insufficient balance.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero"
            )
        
        # Get wallet
        wallet = await WalletService.get_wallet(user_id, db)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Check sufficient balance
        if wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient wallet balance. Current balance: {wallet.balance}"
            )
        
        # Create transaction
        transaction = await WalletService._create_transaction(
            user_id=user_id,
            transaction_type=TransactionType.DEBIT,
            purpose=purpose,
            amount=amount,
            balance_before=wallet.balance,
            description=description,
            db=db
        )
        
        # Update wallet balance
        wallet.balance -= amount
        wallet.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(transaction)
        
        logger.info(f"Deducted {amount} from user_id {user_id}. New balance: {wallet.balance}")
        return transaction
    
    @staticmethod
    async def _create_transaction(
        user_id: int,
        transaction_type: TransactionType,
        purpose: TransactionPurpose,
        amount: float,
        balance_before: float,
        description: Optional[str],
        db: AsyncSession
    ) -> Transaction:
        """Internal method to create transaction record"""
        balance_after = (
            balance_before + amount 
            if transaction_type == TransactionType.CREDIT 
            else balance_before - amount
        )
        
        transaction = Transaction(
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            user_id=user_id,
            transaction_type=transaction_type,
            purpose=purpose,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description
        )
        
        db.add(transaction)
        return transaction
    
    @staticmethod
    async def get_transactions(
        user_id: int,
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> tuple[List[Transaction], int]:
        """Get user's transaction history with pagination"""
        # Get total count
        count_result = await db.execute(
            select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        )
        total = count_result.scalar()
        
        # Get transactions
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        transactions = result.scalars().all()
        
        return list(transactions), total
    
    @staticmethod
    async def check_sufficient_balance(
        user_id: int,
        required_amount: float,
        db: AsyncSession
    ) -> bool:
        """Check if user has sufficient wallet balance"""
        wallet = await WalletService.get_wallet(user_id, db)
        if not wallet:
            return False
        return wallet.balance >= required_amount
    
    @staticmethod
    async def get_wallet_balance(user_id: int, db: AsyncSession) -> float:
        """Get current wallet balance"""
        wallet = await WalletService.get_wallet(user_id, db)
        return wallet.balance if wallet else 0.0
