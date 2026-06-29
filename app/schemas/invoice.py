from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.models.invoice import InvoiceStatus, InvoiceTemplate

class InvoiceItemBase(BaseModel):
    description: str
    quantity: Decimal = Decimal("1.0")
    unit_price: Decimal
    item_id: Optional[UUID] = None

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItem(InvoiceItemBase):
    id: UUID
    invoice_id: UUID
    total_price: Decimal

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    customer_name: str
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    template: InvoiceTemplate = InvoiceTemplate.SIMPLE
    currency: str = "UGX"
    notes: Optional[str] = None
    due_date: Optional[datetime] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    template: Optional[InvoiceTemplate] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None

class Invoice(InvoiceBase):
    id: UUID
    user_id: UUID
    invoice_number: str
    status: InvoiceStatus
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItem]

    class Config:
        from_attributes = True

class InvoiceGenerateRequest(BaseModel):
    text: str
