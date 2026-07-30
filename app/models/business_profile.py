import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    business_name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    tax_id = Column(String, nullable=True)
    registration_number = Column(String, nullable=True)
    
    logo_url = Column(String, nullable=True)
    has_custom_logo = Column(Boolean, default=False)
    
    # List of JSON objects: {type, instructions, is_default}
    default_payment_methods = Column(JSON, default=list)

    user = relationship("User", back_populates="business_profile")

