import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentMethod(str, enum.Enum):
    MTN_UGANDA = "mtn_uganda"
    AIRTEL_UGANDA = "airtel_uganda"
    CARD = "card"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_type = Column(String, nullable=False) # e.g. "monthly_premium", "yearly_pro"
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    currency = Column(String, nullable=False, default="UGX")
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    transaction_ref = Column(String, unique=True, nullable=True) # External ref from provider
    checkout_id = Column(String, unique=True, nullable=True) # Internal session id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="payments")
