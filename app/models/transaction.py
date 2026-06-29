from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum
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
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=True)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False) # Converted to base currency
    currency = Column(String, nullable=False) # Base currency at time of transaction
    original_amount = Column(Numeric(precision=18, scale=2), nullable=True)
    original_currency = Column(String, nullable=True)
    exchange_rate = Column(Numeric(precision=18, scale=6), nullable=True)
    description = Column(String, nullable=True)
    quantity = Column(Numeric(precision=18, scale=2), default=1)
    transaction_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="transactions")
    item = relationship("Item", backref="transactions")
