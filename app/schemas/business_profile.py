from pydantic import BaseModel, EmailStr, HttpUrl
from typing import List, Optional
from uuid import UUID

class PaymentMethodSchema(BaseModel):
    type: str
    instructions: str
    is_default: bool = False

class BusinessProfileBase(BaseModel):
    business_name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    logo_url: Optional[str] = None
    has_custom_logo: bool = False
    default_payment_methods: List[PaymentMethodSchema] = []

class BusinessProfileCreate(BusinessProfileBase):
    pass

class BusinessProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    logo_url: Optional[str] = None
    has_custom_logo: Optional[bool] = None
    default_payment_methods: Optional[List[PaymentMethodSchema]] = None

class BusinessProfile(BusinessProfileBase):
    id: UUID
    user_id: UUID

    class Config:
        from_attributes = True
