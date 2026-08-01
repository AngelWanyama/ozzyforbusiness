import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Invite(Base):
    __tablename__ = "invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(6), index=True, nullable=False)      # the 6-digit code
    business_id = Column(UUID(as_uuid=True), index=True, nullable=False)  # which business they join
    created_by = Column(UUID(as_uuid=True), nullable=False)   # the owner who made it
    phone_number = Column(String, nullable=True)              # optional: who it's meant for
    used = Column(Boolean, default=False, nullable=False)     # one-time use
    expires_at = Column(DateTime, nullable=False)             # 7 days from creation
    created_at = Column(DateTime, default=datetime.utcnow)
