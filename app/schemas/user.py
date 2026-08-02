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

class UserProfile(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    owner_name: Optional[str] = None
    business_description: Optional[str] = None
    years_in_business: Optional[int] = None
    business_location: Optional[str] = None
    email: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None
    notifications_enabled: bool = True
    receipt_template: str = "clean_minimal"
    onboarding_completed: bool = False
    currency: Optional[str] = None
    phone_number: str
    role: str

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    owner_name: Optional[str] = None
    business_description: Optional[str] = None
    years_in_business: Optional[int] = None
    business_location: Optional[str] = None
    email: Optional[str] = None
    contact_phone: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    receipt_template: Optional[str] = None
    onboarding_completed: Optional[bool] = None
    currency: Optional[str] = None
