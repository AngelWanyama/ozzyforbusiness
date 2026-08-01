from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class InviteCreate(BaseModel):
    phone_number: Optional[str] = None  # optional: who the code is for


class InviteResponse(BaseModel):
    code: str
    expires_at: datetime
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True
