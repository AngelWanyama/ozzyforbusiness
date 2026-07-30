from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business_profile import BusinessProfile
from app.schemas.business_profile import (
    BusinessProfile as BusinessProfileSchema,
    BusinessProfileUpdate
)
import os

router = APIRouter()

@router.get("/", response_model=BusinessProfileSchema)
async def get_business_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create a default profile if it doesn't exist
        profile = BusinessProfile(
            user_id=current_user.id,
            business_name=current_user.business_name or "My Business"
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
    return profile

@router.put("/", response_model=BusinessProfileSchema)
async def update_business_profile(
    profile_in: BusinessProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = BusinessProfile(user_id=current_user.id, business_name="My Business")
        db.add(profile)
    
    update_data = profile_in.model_dump(exclude_unset=True)
    if "default_payment_methods" in update_data:
        update_data["default_payment_methods"] = [pm.model_dump() for pm in update_data["default_payment_methods"]]
        
    for field, value in update_data.items():
        setattr(profile, field, value)
        
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/logo", response_model=BusinessProfileSchema)
async def upload_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # In a real app, we'd save to S3 or a local storage service.
    # For now, let's just simulate it.
    UPLOAD_DIR = "/home/team/shared/site/public/logos"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_ext = file.filename.split(".")[-1]
    filename = f"{current_user.id}_logo.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    stmt = select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = BusinessProfile(user_id=current_user.id, business_name="My Business")
        db.add(profile)
        
    profile.logo_url = f"/logos/{filename}"
    profile.has_custom_logo = True
    
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
