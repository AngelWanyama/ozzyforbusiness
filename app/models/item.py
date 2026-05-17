from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base
from sqlalchemy.orm import relationship

class Item(Base):
    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    category = Column(String, nullable=True)
    unit_price = Column(Numeric(precision=18, scale=2), nullable=True)
    stock_level = Column(Numeric(precision=18, scale=2), default=0)
    is_service = Column(Boolean, default=False)

    user = relationship("User", backref="items")
