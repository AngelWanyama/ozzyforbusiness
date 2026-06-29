from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class SettingsUpdate(BaseModel):
    business_name: Optional[str] = None
    owner_name: Optional[str] = None
    business_type: Optional[str] = None
    currency: Optional[str] = None

@router.get("/", response_model=SettingsUpdate)
async def get_settings(current_user: User = Depends(get_current_user)):
    return {
        "business_name": current_user.business_name,
        "owner_name": current_user.owner_name,
        "business_type": current_user.business_type,
        "currency": current_user.currency
    }

@router.put("/", response_model=SettingsUpdate)
async def update_settings(
    settings_in: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user
