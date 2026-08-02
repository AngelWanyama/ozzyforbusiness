from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models.invoice import InvoiceStatus


class InvoiceItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal(1)
    unit_price: Decimal = Decimal(0)


class InvoiceItemOut(InvoiceItemCreate):
    id: UUID
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    items: List[InvoiceItemCreate]


class InvoiceUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class InvoiceGenerateRequest(BaseModel):
    text: str


class InvoiceOut(BaseModel):
    id: UUID
    invoice_number: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    status: InvoiceStatus
    template: str
    total_amount: Decimal
    currency: str
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[InvoiceItemOut] = []

    model_config = ConfigDict(from_attributes=True)
