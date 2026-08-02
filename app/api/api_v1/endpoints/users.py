import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User, PlanType
from app.schemas.user import UserPlan, UserUsage, UserUpgrade, UserProfile, UserProfileUpdate
from datetime import datetime, timedelta

router = APIRouter()

ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5MB

@router.get("/plan", response_model=UserPlan)
async def get_user_plan(current_user: User = Depends(get_current_user)):
    return {
        "plan_type": current_user.plan_type,
        "payment_expiry_date": current_user.payment_expiry_date
    }

@router.get("/usage", response_model=UserUsage)
async def get_user_usage(current_user: User = Depends(get_current_user)):
    return {
        "transactions_this_month": current_user.transactions_this_month,
        "limit": 100 if current_user.plan_type == PlanType.FREE else None
    }

@router.post("/upgrade", response_model=UserPlan)
async def upgrade_user_plan(
    upgrade_data: UserUpgrade,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # In a real app, we'd verify the payment session here
    current_user.plan_type = PlanType.PAID
    # Set expiry to 30 days from now for example
    current_user.payment_expiry_date = datetime.utcnow() + timedelta(days=30)
    
    await db.commit()
    await db.refresh(current_user)

    return {
        "plan_type": current_user.plan_type,
        "payment_expiry_date": current_user.payment_expiry_date
    }

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserProfile)
async def update_me(
    profile: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = profile.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/logo", response_model=UserProfile)
async def upload_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(status_code=400, detail="Logo must be a PNG, JPEG, or WEBP image.")

    contents = await file.read()
    if len(contents) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Logo image must be smaller than 5MB.")

    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads", "logos")
    os.makedirs(uploads_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1] or ".png"
    filename = f"{current_user.id}{ext}"
    file_path = os.path.join(uploads_dir, filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    current_user.logo_url = f"/uploads/logos/{filename}"
    await db.commit()
    await db.refresh(current_user)
    return current_user
