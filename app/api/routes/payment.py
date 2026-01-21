"""
BILLPLZ PAYMENT GATEWAY INTEGRATION (Malaysia)
Wallet Top-up, Subscription purchase, Webhooks
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import requests
import hmac
import hashlib
import secrets
from pydantic import BaseModel, validator

from core.database import get_db
from core.config import settings
from api.deps import get_current_active_user
from models.models import (
    User, Wallet, Transaction, TransactionType, TransactionPurpose,
    Invoice, Subscription, SubscriptionPlan
)
from services.email_service import EmailService

router = APIRouter()

# ==========================================================
# PYDANTIC SCHEMAS
# ==========================================================

class WalletTopUpRequest(BaseModel):
    amount: float
    description: Optional[str] = "Wallet Top-up"

    @validator("amount")
    def validate_amount(cls, v):
        if v < 10:
            raise ValueError("Minimum top-up amount is RM10")
        if v > 10000:
            raise ValueError("Maximum top-up amount is RM10,000")
        return round(v, 2)


class SubscriptionPurchaseRequest(BaseModel):
    plan: str
    billing_cycle: str = "monthly"

    @validator("plan")
    def validate_plan(cls, v):
        if v not in ["starter", "professional", "enterprise"]:
            raise ValueError("Invalid plan")
        return v

    @validator("billing_cycle")
    def validate_cycle(cls, v):
        if v not in ["monthly", "yearly"]:
            raise ValueError("Invalid billing cycle")
        return v

# ==========================================================
# BILLPLZ SERVICE
# ==========================================================

class BillplzService:
    BASE_URL_SANDBOX = "https://www.billplz-sandbox.com/api/v3"
    BASE_URL_PRODUCTION = "https://www.billplz.com/api/v3"

    @staticmethod
    def base_url():
        return (
            BillplzService.BASE_URL_SANDBOX
            if settings.BILLPLZ_SANDBOX
            else BillplzService.BASE_URL_PRODUCTION
        )

    @staticmethod
    def create_bill(**data):
        url = f"{BillplzService.base_url()}/bills"

        response = requests.post(
            url,
            auth=(settings.BILLPLZ_API_KEY, ""),
            data={
                "collection_id": settings.BILLPLZ_COLLECTION_ID,
                "email": data["email"],
                "mobile": data.get("mobile", ""),
                "name": data["name"],
                "amount": int(data["amount"] * 100),
                "description": data["description"],
                "callback_url": data["callback_url"],
                "redirect_url": data["redirect_url"],
                "reference_1_label": "User ID",
                "reference_1": str(data["user_id"]),
                "reference_2_label": "Transaction ID",
                "reference_2": data["transaction_id"],
            },
            timeout=20,
        )

        if not response.ok:
            raise HTTPException(status_code=500, detail=f"Billplz API error: {response.text}")

        return response.json()

    @staticmethod
    def verify_signature(payload: dict, signature: str) -> bool:
        if not settings.BILLPLZ_X_SIGNATURE_KEY:
            return True  # dev mode

        payload = payload.copy()
        payload.pop("x_signature", None)

        signing_string = "&".join(
            f"{k}={payload[k]}" for k in sorted(payload.keys())
        )

        expected = hmac.new(
            settings.BILLPLZ_X_SIGNATURE_KEY.encode(),
            signing_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

# ==========================================================
# WALLET TOP-UP
# ==========================================================

@router.post("/wallet/topup")
async def wallet_topup(
    req: WalletTopUpRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    wallet = db.query(Wallet).filter_by(user_id=user.id).first()
    if not wallet:
        raise HTTPException(404, "Wallet not found")

    txn_id = f"TOP{secrets.token_hex(8).upper()}"

    txn = Transaction(
        transaction_id=txn_id,
        user_id=user.id,
        transaction_type=TransactionType.CREDIT,
        purpose=TransactionPurpose.WALLET_TOPUP,
        amount=req.amount,
        balance_before=wallet.balance,
        balance_after=wallet.balance,  # will update after payment confirmed
        status="pending",
        payment_method="billplz",
        meta_data={},  # Using meta_data instead of reserved 'metadata'
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    bill = BillplzService.create_bill(
        email=user.email,
        name=user.full_name,
        mobile=user.phone_number,
        amount=req.amount,
        description="Wallet Top-up",
        callback_url=f"{settings.BACKEND_URL}/api/payment/billplz/callback",
        redirect_url=f"{settings.FRONTEND_URL}/payment/success",
        user_id=user.id,
        transaction_id=txn_id,
    )

    txn.payment_gateway_id = bill.get("id")
    if not txn.meta_data:
        txn.meta_data = {}
    txn.meta_data["billplz_url"] = bill.get("url")
    db.commit()

    return {"payment_url": bill.get("url"), "transaction_id": txn_id}

# ==========================================================
# SUBSCRIPTION PURCHASE
# ==========================================================

@router.post("/subscription/purchase")
async def purchase_subscription(
    req: SubscriptionPurchaseRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    pricing = {
        "starter": {"monthly": 99, "yearly": 990},
        "professional": {"monthly": 299, "yearly": 2990},
        "enterprise": {"monthly": 999, "yearly": 9990},
    }

    amount = pricing[req.plan][req.billing_cycle]
    txn_id = f"SUB{secrets.token_hex(8).upper()}"

    txn = Transaction(
        transaction_id=txn_id,
        user_id=user.id,
        transaction_type=TransactionType.DEBIT,
        purpose=TransactionPurpose.SUBSCRIPTION,
        amount=amount,
        status="pending",
        payment_method="billplz",
        meta_data={"plan": req.plan, "cycle": req.billing_cycle},  # Using meta_data instead of reserved 'metadata'
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    bill = BillplzService.create_bill(
        email=user.email,
        name=user.full_name,
        mobile=user.phone_number,
        amount=amount,
        description=f"Subscription {req.plan}",
        callback_url=f"{settings.BACKEND_URL}/api/payment/billplz/callback",
        redirect_url=f"{settings.FRONTEND_URL}/subscription/success",
        user_id=user.id,
        transaction_id=txn_id,
    )

    txn.payment_gateway_id = bill.get("id")
    if not txn.meta_data:
        txn.meta_data = {}
    txn.meta_data["billplz_url"] = bill.get("url")
    db.commit()

    return {"payment_url": bill.get("url"), "transaction_id": txn_id}

# ==========================================================
# BILLPLZ WEBHOOK
# ==========================================================

@router.post("/billplz/callback")
async def billplz_callback(
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    form = dict(await request.form())
    signature = form.get("x_signature", "")

    if not BillplzService.verify_signature(form, signature):
        raise HTTPException(401, "Invalid signature")

    txn_id = form.get("reference_2")
    paid = str(form.get("paid")).lower() in ["true", "1"]
    state = form.get("state")

    txn = db.query(Transaction).filter_by(transaction_id=txn_id).first()
    if not txn or txn.status != "pending":
        return {"status": "ignored"}

    if paid and state == "paid":
        txn.status = "completed"

        if txn.purpose == TransactionPurpose.WALLET_TOPUP:
            wallet = db.query(Wallet).filter_by(user_id=txn.user_id).first()
            wallet.balance += txn.amount
            txn.balance_after = wallet.balance

        if txn.purpose == TransactionPurpose.SUBSCRIPTION:
            # extend existing subscription if active
            existing_sub = db.query(Subscription).filter_by(
                user_id=txn.user_id, plan=SubscriptionPlan[txn.meta_data["plan"].upper()],
                status="active"
            ).first()

            duration = timedelta(days=365 if txn.meta_data["cycle"] == "yearly" else 30)
            now = datetime.utcnow()

            if existing_sub and existing_sub.current_period_end > now:
                existing_sub.current_period_end += duration
            else:
                sub = Subscription(
                    user_id=txn.user_id,
                    plan=SubscriptionPlan[txn.meta_data["plan"].upper()],
                    status="active",
                    started_at=now,
                    current_period_end=now + duration,
                )
                db.add(sub)

        db.commit()
        return {"status": "success"}

    txn.status = "failed"
    db.commit()
    return {"status": "failed"}
