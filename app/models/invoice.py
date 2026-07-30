from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, JSON
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
    TEMPLATE_A = "template_a"
    TEMPLATE_B = "template_b"
    TEMPLATE_C = "template_c"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    invoice_number = Column(String, nullable=False)
    invoice_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    currency = Column(String, default="UGX")
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    template_id = Column(SQLEnum(InvoiceTemplate), default=InvoiceTemplate.TEMPLATE_A)
    
    # Customer info
    customer_name = Column(String, nullable=False)
    customer_company = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    customer_address = Column(String, nullable=True)
    
    # Totals
    subtotal = Column(Numeric(precision=18, scale=2), default=0)
    total_discount = Column(Numeric(precision=18, scale=2), default=0)
    total_tax = Column(Numeric(precision=18, scale=2), default=0)
    grand_total = Column(Numeric(precision=18, scale=2), default=0)
    
    # List of JSON objects: {type, instructions, is_default}
    payment_methods = Column(JSON, default=list)
    
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=True)
    
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    quantity = Column(Numeric(precision=18, scale=2), default=1)
    unit_price = Column(Numeric(precision=18, scale=2), nullable=False)
    discount_pct = Column(Numeric(precision=5, scale=2), default=0)
    tax_pct = Column(Numeric(precision=5, scale=2), default=0)
    
    # total_price = (unit_price * quantity) * (1 - discount_pct/100) * (1 + tax_pct/100) ? 
    # Or subtotal = unit_price * quantity, then calculate discount and tax.
    # We'll store the calculated total for this line.
    line_total = Column(Numeric(precision=18, scale=2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")

