from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base
from sqlalchemy.orm import relationship
import enum

class TransactionType(str, enum.Enum):
    SALE = "sale"
    EXPENSE = "expense"
    INVENTORY_ADJUSTMENT = "inventory_adjustment"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    business_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=True)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)  # e.g. "Sales Revenue", "Utilities", "Transport" — from the NLP parser
    quantity = Column(Numeric(precision=18, scale=2), default=1)
    # Snapshot of cost of goods sold at the moment of sale (sum of buying_price * quantity across
    # every line item), not a live lookup against the item's current buying_price -- a later price
    # change must never rewrite a past sale's recorded margin. Null/not applicable for an expense.
    # cost_of_goods_complete is False whenever any line item in the sale had no matched product or
    # no buying_price on file, so the figure is a known lower bound, not silently treated as zero.
    cost_of_goods = Column(Numeric(precision=18, scale=2), nullable=True)
    cost_of_goods_complete = Column(Boolean, nullable=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], backref="transactions")
    item = relationship("Item", backref="transactions")
