from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
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
    from app.services.currency_service import currency_service
    from decimal import Decimal
    
    # Check limit for FREE users
    if current_user.plan_type == PlanType.FREE and current_user.transactions_this_month >= 100:
        raise HTTPException(
            status_code=403, 
            detail="Transaction limit reached for FREE plan. Please upgrade to PAID for unlimited transactions."
        )

    # Handle currency conversion
    amount = transaction_in.amount
    currency = transaction_in.currency
    original_amount = amount
    original_currency = currency
    exchange_rate = Decimal("1.0")
    
    if currency != current_user.currency:
        amount, exchange_rate = await currency_service.convert(amount, currency, current_user.currency)
        currency = current_user.currency

    transaction = TransactionModel(
        **transaction_in.model_dump(exclude={"amount", "currency", "original_amount", "original_currency", "exchange_rate"}),
        amount=amount,
        currency=currency,
        original_amount=original_amount,
        original_currency=original_currency,
        exchange_rate=exchange_rate,
        user_id=current_user.id
    )
    db.add(transaction)
    
    # Increment usage counter
    current_user.transactions_this_month += 1
    db.add(current_user)
    
    await db.commit()
    await db.refresh(transaction)
    return transaction

@router.post("/categories/correct")
async def correct_category(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    item_name: str,
    corrected_category: str
):
    from app.models.category_correction import CategoryCorrection
    
    stmt = select(CategoryCorrection).where(
        CategoryCorrection.user_id == current_user.id,
        CategoryCorrection.item_name == item_name
    )
    result = await db.execute(stmt)
    correction = result.scalar_one_or_none()
    
    if correction:
        correction.corrected_category = corrected_category
        correction.count += 1
    else:
        correction = CategoryCorrection(
            user_id=current_user.id,
            item_name=item_name,
            corrected_category=corrected_category
        )
        db.add(correction)
        
    await db.commit()
    return {"message": "Category correction saved"}

@router.get("/", response_model=TransactionHistory)
async def read_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    # Total count
    count_stmt = select(func.count()).select_from(TransactionModel).where(TransactionModel.user_id == current_user.id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # Items
    stmt = select(TransactionModel).where(TransactionModel.user_id == current_user.id).offset(skip).limit(limit).order_by(TransactionModel.transaction_date.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {"total": total, "items": items}

@router.post("/process-raw", response_model=Transaction)
async def process_raw_transaction(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    raw_text: str = Query(..., description="The raw business entry text")
):
    """
    Parse a raw text entry and record it as a transaction.
    """
    from app.services.nlp_parser import nlp_parser
    from app.models.user import PlanType
    from datetime import datetime
    
    # Check limit for FREE users
    if current_user.plan_type == PlanType.FREE and current_user.transactions_this_month >= 100:
        raise HTTPException(
            status_code=403, 
            detail="Transaction limit reached for FREE plan. Please upgrade to PAID for unlimited transactions."
        )

    # Parse text
    parsed = await nlp_parser.parse_transaction(raw_text)
    
    if parsed.intent not in ["sale", "expense"]:
         raise HTTPException(status_code=400, detail=f"Entry detected as '{parsed.intent}', but this endpoint only records sales and expenses.")

    # Convert NLP response to transaction model
    transaction_date = datetime.utcnow()
    if parsed.transaction_date:
        try:
            transaction_date = datetime.strptime(parsed.transaction_date, "%Y-%m-%d")
        except ValueError:
            pass

    transaction = TransactionModel(
        user_id=current_user.id,
        type=parsed.intent,
        amount=parsed.amount,
        currency=parsed.currency,
        description=parsed.item,
        quantity=parsed.quantity,
        transaction_date=transaction_date
    )
    
    db.add(transaction)
    
    # Increment usage counter
    current_user.transactions_this_month += 1
    db.add(current_user)
    
    await db.commit()
    await db.refresh(transaction)
    return transaction
