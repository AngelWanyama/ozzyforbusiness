from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
import uuid
import sqlalchemy as sa
from datetime import datetime
from app.core.database import Base

class SummaryType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class Summary(Base):
    __tablename__ = "summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(SQLEnum(SummaryType), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    total_sales = Column(sa.Numeric(precision=18, scale=2), default=0)
    total_expenses = Column(sa.Numeric(precision=18, scale=2), default=0)
    profit = Column(sa.Numeric(precision=18, scale=2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
