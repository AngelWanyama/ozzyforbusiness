from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base
from sqlalchemy.orm import relationship

class CategoryCorrection(Base):
    __tablename__ = "category_corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    item_name = Column(String, index=True, nullable=False)
    corrected_category = Column(String, nullable=False)
    count = Column(Integer, default=1)

    user = relationship("User", backref="category_corrections")
