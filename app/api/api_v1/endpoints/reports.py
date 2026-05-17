from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import SummaryReport
from decimal import Decimal

router = APIRouter()

@router.get("/summary", response_model=SummaryReport)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Sum sales
    sales_stmt = select(func.sum(Transaction.amount)).where(
        Transaction.user_id == current_user.id,
        Transaction.type == TransactionType.SALE
    )
    sales_result = await db.execute(sales_stmt)
    total_sales = sales_result.scalar() or Decimal(0)

    # Sum expenses
    expenses_stmt = select(func.sum(Transaction.amount)).where(
        Transaction.user_id == current_user.id,
        Transaction.type == TransactionType.EXPENSE
    )
    expenses_result = await db.execute(expenses_stmt)
    total_expenses = expenses_result.scalar() or Decimal(0)

    return {
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "net_profit": total_sales - total_expenses,
        "currency": current_user.currency
    }
