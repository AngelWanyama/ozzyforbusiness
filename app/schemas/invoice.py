from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.models.invoice import InvoiceStatus, InvoiceTemplate

class PaymentMethodSchema(BaseModel):
    type: str
    instructions: str
    is_default: bool = False

class InvoiceItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: Decimal = Decimal("1.0")
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0.0")
    tax_pct: Decimal = Decimal("0.0")
    item_id: Optional[UUID] = None

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItem(InvoiceItemBase):
    id: UUID
    invoice_id: UUID
    line_total: Decimal

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    currency: str = "UGX"
    template_id: InvoiceTemplate = InvoiceTemplate.TEMPLATE_A
    
    # Customer info
    customer_name: str
    customer_company: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    
    payment_methods: List[PaymentMethodSchema] = []
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    template_id: Optional[InvoiceTemplate] = None
    customer_name: Optional[str] = None
    customer_company: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    payment_methods: Optional[List[PaymentMethodSchema]] = None
    notes: Optional[str] = None

class Invoice(InvoiceBase):
    id: UUID
    user_id: UUID
    status: InvoiceStatus
    subtotal: Decimal
    total_discount: Decimal
    total_tax: Decimal
    grand_total: Decimal
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItem]

    class Config:
        from_attributes = True

class InvoiceGenerateRequest(BaseModel):
    text: str
