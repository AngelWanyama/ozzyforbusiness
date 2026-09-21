import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ChatProposal(Base):
    """A PROPOSE-step result awaiting a real, separate confirmation message before any
    database write happens — the mechanism Appendix A of the Ozzy Behaviour Intelligence
    Brain calls the PROPOSE/COMMIT state machine. The AI model is never trusted to self-report
    that the entrepreneur confirmed something; the application layer checks the next inbound
    message against the stored proposal here instead."""

    __tablename__ = "chat_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    function_name = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    preview_text = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending | committed | cancelled | superseded | expired
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
