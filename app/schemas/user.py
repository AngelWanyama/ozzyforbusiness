from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.user import PlanType

class UserPlan(BaseModel):
    plan_type: PlanType
    payment_expiry_date: Optional[datetime] = None

class UserUsage(BaseModel):
    transactions_this_month: int
    limit: Optional[int] = None

class UserUpgrade(BaseModel):
    payment_ref: str # Reference from M-Pesa or Card payment
