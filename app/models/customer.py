import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    outstanding_balance = Column(Numeric(precision=18, scale=2), nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
