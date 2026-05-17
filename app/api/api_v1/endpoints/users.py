from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User, PlanType
from app.schemas.user import UserPlan, UserUsage, UserUpgrade
from datetime import datetime, timedelta

router = APIRouter()

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
