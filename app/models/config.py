from sqlalchemy import Column, String, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class Config(Base):
    __tablename__ = "configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(String, nullable=True)
