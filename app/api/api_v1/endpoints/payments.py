from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_db, get_current_user
from app.models.user import User, PlanType
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.schemas.payment import PaymentSchema, MobileMoneyInitiateRequest
from app.services.mtn_uganda import mtn_ug_service
from app.services.airtel_uganda import airtel_ug_service
from app.services.flutterwave import flutterwave_service
from datetime import datetime, timedelta
import uuid

router = APIRouter()

@router.post("/mobile-money/initiate", response_model=dict)
async def initiate_mobile_money_payment(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payment_in: MobileMoneyInitiateRequest
):
    method = PaymentMethod.MTN_UGANDA if payment_in.provider.lower() == "mtn" else PaymentMethod.AIRTEL_UGANDA
    
    # 1. Create a pending payment record
    payment = Payment(
        user_id=current_user.id,
        plan_type=payment_in.plan_type,
        amount=payment_in.amount,
        currency="UGX",
        payment_method=method,
        status=PaymentStatus.PENDING
    )
    db.add(payment)
    await db.flush()

    # 2. Call the respective service
    external_id = str(payment.id)
    if payment_in.provider.lower() == "mtn":
        response = await mtn_ug_service.initiate_payment(
            phone_number=payment_in.phone_number,
            amount=payment_in.amount,
            external_id=external_id
        )
        payment.checkout_id = response.get("reference_id")
    else:
        response = await airtel_ug_service.initiate_payment(
            phone_number=payment_in.phone_number,
            amount=payment_in.amount,
            reference=external_id
        )
        payment.checkout_id = response.get("transaction_id")

    await db.commit()
    return response

@router.post("/webhook/mtn")
async def mtn_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    # Logic to handle MTN callback
    # Update payment status and upgrade user
    return {"status": "ok"}

@router.post("/webhook/airtel")
async def airtel_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    # Logic to handle Airtel callback
    return {"status": "ok"}

@router.post("/card/checkout", response_model=dict)
async def create_card_payment(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    amount: float = Query(...),
    plan_type: str = Query(...)
):
    tx_ref = f"ozzy_{uuid.uuid4().hex[:10]}"
    
    payment = Payment(
        user_id=current_user.id,
        plan_type=plan_type,
        amount=amount,
        currency="UGX",
        payment_method=PaymentMethod.CARD,
        status=PaymentStatus.PENDING,
        transaction_ref=tx_ref
    )
    db.add(payment)
    await db.commit()

    response = await flutterwave_service.create_payment_link(
        tx_ref=tx_ref,
        amount=amount,
        currency="UGX",
        user_email=f"{current_user.phone_number}@ozzy.com",
        user_name=current_user.business_name or "Ozzy User"
    )

    return response

@router.get("/history", response_model=List[PaymentSchema])
async def get_payment_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Payment).where(Payment.user_id == current_user.id).order_by(Payment.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user)
):
    is_active = False
    if current_user.plan_type == PlanType.PAID:
        if current_user.payment_expiry_date and current_user.payment_expiry_date > datetime.utcnow():
            is_active = True
    
    return {
        "plan_type": current_user.plan_type,
        "is_active": is_active,
        "expiry_date": current_user.payment_expiry_date
    }
