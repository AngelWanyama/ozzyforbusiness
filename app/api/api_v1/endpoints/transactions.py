from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.transaction import Transaction as TransactionModel
from app.schemas.transaction import Transaction, TransactionCreate, TransactionHistory
import uuid

router = APIRouter()

@router.post("/", response_model=Transaction)
async def create_transaction(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    transaction_in: TransactionCreate
):
    from app.models.user import PlanType
    
    # Check limit for FREE users
    if current_user.plan_type == PlanType.FREE and current_user.transactions_this_month >= 100:
        raise HTTPException(
            status_code=403, 
            detail="Transaction limit reached for FREE plan. Please upgrade to PAID for unlimited transactions."
        )

    # Fall back to the user's own id if they somehow have no business_id yet
    # (should not happen post Stage A backfill, but keeps this endpoint safe).
    effective_business_id = current_user.business_id or current_user.id

    transaction = TransactionModel(
        **transaction_in.model_dump(),
        user_id=current_user.id,
        business_id=effective_business_id
    )
    db.add(transaction)
    
    # Increment usage counter
    current_user.transactions_this_month += 1
    db.add(current_user)
    
    await db.commit()
    await db.refresh(transaction)
    return transaction

@router.get("/", response_model=TransactionHistory)
async def read_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    # Fall back to the user's own id if they somehow have no business_id yet
    # (should not happen post Stage A backfill, but keeps this endpoint safe).
    effective_business_id = current_user.business_id or current_user.id

    filters = [TransactionModel.business_id == effective_business_id]

    # Workers can only see the past week's activity, regardless of skip/limit.
    if current_user.role == "worker":
        filters.append(TransactionModel.transaction_date >= datetime.utcnow() - timedelta(days=7))

    # Total count
    count_stmt = select(func.count()).select_from(TransactionModel).where(*filters)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # Items
    stmt = select(TransactionModel).where(*filters).offset(skip).limit(limit).order_by(TransactionModel.transaction_date.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {"total": total, "items": items}
