from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base
from sqlalchemy.orm import relationship
import enum

class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"

class InvoiceTemplate(str, enum.Enum):
    SIMPLE = "simple"
    PROFESSIONAL = "professional"
    MODERN = "modern"
    CUSTOM = "custom"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    customer_address = Column(String, nullable=True)
    
    invoice_number = Column(String, nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    template = Column(SQLEnum(InvoiceTemplate), default=InvoiceTemplate.SIMPLE)
    
    total_amount = Column(Numeric(precision=18, scale=2), default=0)
    currency = Column(String, default="UGX")
    
    notes = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=True)
    
    description = Column(String, nullable=False)
    quantity = Column(Numeric(precision=18, scale=2), default=1)
    unit_price = Column(Numeric(precision=18, scale=2), nullable=False)
    total_price = Column(Numeric(precision=18, scale=2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
