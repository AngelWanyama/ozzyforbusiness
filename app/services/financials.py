"""
Shared profit/COGS calculation, used everywhere profit is reported: chat answers, the Reports
tab, the dashboard, PDF exports, and daily/weekly digests feeding greetings.

Confirmed 2026-09-23: every one of those call sites independently computed
net_profit = total_sales - total_expenses. Cost of goods sold was never subtracted anywhere,
despite buying_price being collected during onboarding and every product-add flow -- a real sale
of an item bought for 15,000 and sold for 30,000 showed as if the full 30,000 were pure profit.
One shared calculation from here on, not four formulas quietly drifting out of sync.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType


@dataclass
class PeriodFinancials:
    total_sales: Decimal
    total_expenses: Decimal
    cost_of_goods: Decimal
    # False whenever any sale in the period is missing cost data (an unmatched product, a
    # product with no buying_price on file, or a sale recorded before this feature existed).
    # Per the explicit rule this was built to satisfy: unknown cost is never silently treated as
    # zero, so callers must check this and caveat the profit figure rather than presenting it as
    # certain when it isn't.
    cogs_known_complete: bool
    net_profit: Decimal


async def calculate_period_financials(db: AsyncSession, business_id, start: datetime, end: datetime) -> PeriodFinancials:
    stmt = select(Transaction).where(
        Transaction.business_id == business_id,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
    )
    rows = (await db.execute(stmt)).scalars().all()

    total_sales = Decimal(0)
    total_expenses = Decimal(0)
    cost_of_goods = Decimal(0)
    cogs_known_complete = True

    for t in rows:
        if t.type == TransactionType.SALE:
            total_sales += t.amount
            if t.cost_of_goods is not None:
                cost_of_goods += t.cost_of_goods
            if t.cost_of_goods is None or t.cost_of_goods_complete is False:
                cogs_known_complete = False
        elif t.type == TransactionType.EXPENSE:
            total_expenses += t.amount

    net_profit = total_sales - cost_of_goods - total_expenses
    return PeriodFinancials(
        total_sales=total_sales, total_expenses=total_expenses, cost_of_goods=cost_of_goods,
        cogs_known_complete=cogs_known_complete, net_profit=net_profit,
    )


def cogs_caveat(financials: PeriodFinancials) -> str:
    """One honest sentence to append whenever cogs_known_complete is False, instead of quietly
    presenting a profit figure that may be missing real cost of goods."""
    if financials.cogs_known_complete:
        return ""
    return " (Note: some sold items don't have a buying price on file yet, so actual profit may be a bit lower than this.)"
