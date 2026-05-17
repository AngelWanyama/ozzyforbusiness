from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.payment import PaymentMethod, PaymentStatus
from decimal import Decimal

class PaymentBase(BaseModel):
    plan_type: str
    amount: Decimal
    currency: str = "UGX"
    payment_method: PaymentMethod

class PaymentCreate(PaymentBase):
    phone_number: Optional[str] = None

class PaymentUpdate(BaseModel):
    status: PaymentStatus
    transaction_ref: Optional[str] = None

class PaymentSchema(PaymentBase):
    id: str
    status: PaymentStatus
    transaction_ref: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MobileMoneyInitiateRequest(BaseModel):
    amount: int
    phone_number: str
    plan_type: str
    provider: str # "mtn" or "airtel"

class MpesaCallback(BaseModel): # Keeping name generic or removing if not needed
    Body: dict
