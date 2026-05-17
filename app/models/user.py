import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class PlanType(str, enum.Enum):
    FREE = "FREE"
    PAID = "PAID"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    business_name = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    currency = Column(String, default="UGX")
    plan_type = Column(SQLEnum(PlanType), default=PlanType.FREE, nullable=False)
    transactions_this_month = Column(Integer, default=0, nullable=False)
    last_transaction_at = Column(DateTime, nullable=True)
    payment_expiry_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
