from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from app.api.deps import get_db, require_owner
from app.models.user import User
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import SummaryReport
from app.schemas.report import ReportDashboard, DailyPoint, CategorySlice, BestSeller

router = APIRouter()

PERIOD_WINDOWS = {
    "today": timedelta(hours=0),  # handled specially: since midnight, not a rolling window
    "week": timedelta(days=7),
    "month": timedelta(days=30),
}


def _period_bounds(period: str, now: datetime) -> tuple[datetime, datetime, datetime, datetime]:
    """Returns (current_start, current_end, previous_start, previous_end)."""
    if period == "today":
        current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        span = now - current_start
    else:
        span = PERIOD_WINDOWS.get(period, PERIOD_WINDOWS["month"])
        current_start = now - span
    current_end = now
    previous_end = current_start
    previous_start = current_start - span if span.total_seconds() > 0 else current_start - timedelta(days=1)
    return current_start, current_end, previous_start, previous_end


async def _sum_by_type(db: AsyncSession, business_id, tx_type: TransactionType, start: datetime, end: datetime) -> Decimal:
    stmt = select(func.sum(Transaction.amount)).where(
        Transaction.business_id == business_id,
        Transaction.type == tx_type,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
    )
    result = await db.execute(stmt)
    return result.scalar() or Decimal(0)


def _pct_change(current: Decimal, previous: Decimal) -> Optional[float]:
    if previous == 0:
        return None  # nothing to meaningfully compare against
    return float((current - previous) / previous * 100)

@router.get("/summary", response_model=SummaryReport)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    # Fall back to the user's own id if they somehow have no business_id yet
    # (should not happen post Stage A backfill, but keeps this endpoint safe).
    effective_business_id = current_user.business_id or current_user.id

    # Sum sales
    sales_stmt = select(func.sum(Transaction.amount)).where(
        Transaction.business_id == effective_business_id,
        Transaction.type == TransactionType.SALE
    )
    sales_result = await db.execute(sales_stmt)
    total_sales = sales_result.scalar() or Decimal(0)

    # Sum expenses
    expenses_stmt = select(func.sum(Transaction.amount)).where(
        Transaction.business_id == effective_business_id,
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


@router.get("/dashboard", response_model=ReportDashboard)
async def get_dashboard(
    period: str = Query("month", pattern="^(today|week|month)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    effective_business_id = current_user.business_id or current_user.id
    now = datetime.utcnow()
    cur_start, cur_end, prev_start, prev_end = _period_bounds(period, now)

    total_sales = await _sum_by_type(db, effective_business_id, TransactionType.SALE, cur_start, cur_end)
    total_expenses = await _sum_by_type(db, effective_business_id, TransactionType.EXPENSE, cur_start, cur_end)
    prev_sales = await _sum_by_type(db, effective_business_id, TransactionType.SALE, prev_start, prev_end)
    prev_expenses = await _sum_by_type(db, effective_business_id, TransactionType.EXPENSE, prev_start, prev_end)

    # Weekly performance chart: always the last 7 calendar days, regardless of the period toggle.
    daily: list[DailyPoint] = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_sales = await _sum_by_type(db, effective_business_id, TransactionType.SALE, day_start, day_end)
        day_expenses = await _sum_by_type(db, effective_business_id, TransactionType.EXPENSE, day_start, day_end)
        daily.append(DailyPoint(
            label=day_start.strftime("%a"),
            date=day_start.strftime("%Y-%m-%d"),
            sales=day_sales,
            expenses=day_expenses,
        ))

    # Category mix: where expense money went this period.
    category_stmt = select(
        func.coalesce(Transaction.category, "Other"),
        func.sum(Transaction.amount),
    ).where(
        Transaction.business_id == effective_business_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.transaction_date >= cur_start,
        Transaction.transaction_date <= cur_end,
    ).group_by(func.coalesce(Transaction.category, "Other"))
    category_result = await db.execute(category_stmt)
    category_rows = category_result.all()
    category_total = sum((row[1] for row in category_rows), Decimal(0))
    category_breakdown = [
        CategorySlice(
            category=row[0],
            amount=row[1],
            percent=float(row[1] / category_total * 100) if category_total > 0 else 0.0,
        )
        for row in sorted(category_rows, key=lambda r: r[1], reverse=True)
    ]

    # Best sellers: top products by revenue this period (grouped by what was actually typed in Chat).
    best_stmt = select(
        func.coalesce(Transaction.description, "Item"),
        func.sum(Transaction.quantity),
        func.sum(Transaction.amount),
    ).where(
        Transaction.business_id == effective_business_id,
        Transaction.type == TransactionType.SALE,
        Transaction.transaction_date >= cur_start,
        Transaction.transaction_date <= cur_end,
    ).group_by(func.coalesce(Transaction.description, "Item")).order_by(func.sum(Transaction.amount).desc()).limit(5)
    best_result = await db.execute(best_stmt)
    best_sellers = [BestSeller(name=row[0], units=row[1] or Decimal(0), revenue=row[2] or Decimal(0)) for row in best_result.all()]

    return ReportDashboard(
        period=period,
        currency=current_user.currency,
        total_sales=total_sales,
        total_expenses=total_expenses,
        net_profit=total_sales - total_expenses,
        sales_change_pct=_pct_change(total_sales, prev_sales),
        expenses_change_pct=_pct_change(total_expenses, prev_expenses),
        daily=daily,
        category_breakdown=category_breakdown,
        best_sellers=best_sellers,
    )


@router.get("/dashboard/pdf")
async def get_dashboard_pdf(
    period: str = Query("month", pattern="^(today|week|month)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    from app.services.report_engine import report_engine
    dashboard = await get_dashboard(period=period, db=db, current_user=current_user)
    pdf_content = report_engine.export_dashboard_pdf(dashboard, current_user)
    filename = f"ozzy_report_{period}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
