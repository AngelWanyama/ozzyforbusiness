from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction, TransactionType
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.user import User

# Uganda runs on East Africa Time (UTC+3, no daylight saving) — everything in this app is
# stored as naive UTC, so greetings are computed in EAT just for the purposes of deciding
# "good morning" vs "good evening" and what counts as "today".
EAT_OFFSET = timedelta(hours=3)

LOW_STOCK_THRESHOLD = Decimal(5)  # no reorder-point field exists yet; a small fixed threshold is a reasonable stand-in
WEEKLY_MILESTONE_PCT = 15.0       # how much this week must beat last week by to count as a "milestone"
SLOW_DAY_RATIO = 0.7              # today-so-far must be under 70% of yesterday-at-this-same-time to count as "slow"


async def _sum_amount(db: AsyncSession, business_id, tx_type: TransactionType, start: datetime, end: datetime) -> Decimal:
    stmt = select(func.sum(Transaction.amount)).where(
        Transaction.business_id == business_id,
        Transaction.type == tx_type,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
    )
    result = await db.execute(stmt)
    return result.scalar() or Decimal(0)


async def _count_transactions(db: AsyncSession, business_id, tx_type: TransactionType, start: datetime, end: datetime) -> int:
    stmt = select(func.count()).select_from(Transaction).where(
        Transaction.business_id == business_id,
        Transaction.type == tx_type,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _biggest_expense_category(db: AsyncSession, business_id, start: datetime, end: datetime) -> Optional[str]:
    stmt = select(
        func.coalesce(Transaction.category, "Other"), func.sum(Transaction.amount)
    ).where(
        Transaction.business_id == business_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
    ).group_by(func.coalesce(Transaction.category, "Other")).order_by(func.sum(Transaction.amount).desc()).limit(1)
    result = await db.execute(stmt)
    row = result.first()
    return row[0] if row else None


def _fmt(currency: str, amount) -> str:
    return f"{currency} {float(amount):,.0f}"


async def get_greeting(db: AsyncSession, user: User) -> Dict[str, Any]:
    business_id = user.business_id or user.id
    currency = user.currency
    name = user.owner_name or user.business_name or "there"

    now_eat = datetime.utcnow() + EAT_OFFSET
    today_start_eat = now_eat.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_eat - EAT_OFFSET
    yesterday_start_utc = today_start_utc - timedelta(days=1)
    now_utc = datetime.utcnow()

    today_sales = await _sum_amount(db, business_id, TransactionType.SALE, today_start_utc, now_utc)
    today_expenses = await _sum_amount(db, business_id, TransactionType.EXPENSE, today_start_utc, now_utc)
    yesterday_sales = await _sum_amount(db, business_id, TransactionType.SALE, yesterday_start_utc, today_start_utc)
    yesterday_expenses = await _sum_amount(db, business_id, TransactionType.EXPENSE, yesterday_start_utc, today_start_utc)
    yesterday_partial_cutoff = yesterday_start_utc + (now_utc - today_start_utc)
    yesterday_partial_sales = await _sum_amount(db, business_id, TransactionType.SALE, yesterday_start_utc, yesterday_partial_cutoff)

    this_week_start = today_start_utc - timedelta(days=6)
    last_week_start = this_week_start - timedelta(days=7)
    this_week_sales = await _sum_amount(db, business_id, TransactionType.SALE, this_week_start, now_utc)
    last_week_sales = await _sum_amount(db, business_id, TransactionType.SALE, last_week_start, this_week_start)

    # Best single day this month so far, excluding today (so "today" can be fairly compared against it).
    month_start_utc = today_start_eat.replace(day=1) - EAT_OFFSET
    best_day_sales = Decimal(0)
    if today_start_utc > month_start_utc:
        day_stmt = select(
            func.date(Transaction.transaction_date), func.sum(Transaction.amount)
        ).where(
            Transaction.business_id == business_id,
            Transaction.type == TransactionType.SALE,
            Transaction.transaction_date >= month_start_utc,
            Transaction.transaction_date < today_start_utc,
        ).group_by(func.date(Transaction.transaction_date))
        day_result = await db.execute(day_stmt)
        day_totals = [row[1] or Decimal(0) for row in day_result.all()]
        if day_totals:
            best_day_sales = max(day_totals)

    low_stock_stmt = select(Item.name).where(
        Item.user_id == user.id,  # Item isn't business-scoped yet (pre-existing gap, out of scope here)
        Item.stock_level > 0,
        Item.stock_level <= LOW_STOCK_THRESHOLD,
    )
    low_stock_result = await db.execute(low_stock_stmt)
    low_stock_items = [row[0] for row in low_stock_result.all()]

    outstanding_stmt = select(func.count(), func.sum(Invoice.total_amount)).where(
        Invoice.business_id == business_id,
        Invoice.status.in_(["sent", "overdue"]),
    )
    outstanding_result = await db.execute(outstanding_stmt)
    outstanding_count, outstanding_total = outstanding_result.one()
    outstanding_count = outstanding_count or 0
    outstanding_total = outstanding_total or Decimal(0)

    hour = now_eat.hour
    time_of_day = "morning" if hour < 12 else ("midday" if hour < 17 else "evening")

    weekly_pct = float((this_week_sales - last_week_sales) / last_week_sales * 100) if last_week_sales > 0 else None
    no_activity_today = today_sales == 0 and today_expenses == 0

    # Priority order: only one scenario wins per login.
    if weekly_pct is not None and weekly_pct >= WEEKLY_MILESTONE_PCT and this_week_sales > 0:
        return {
            "scenario": "weekly_milestone",
            "text": f"🎉 Congratulations! You've reached {_fmt(currency, this_week_sales)} in sales this week. That's {weekly_pct:.0f}% higher than last week.",
            "chips": ["View this week's activity", "Create a report", "Record a sale"],
        }

    if time_of_day == "morning" and outstanding_count > 0:
        return {
            "scenario": "outstanding_invoices",
            "text": f"👋 Good morning, {name}. You have {outstanding_count} unpaid invoice{'s' if outstanding_count != 1 else ''} worth {_fmt(currency, outstanding_total)}. Following up with those customers could improve your cash flow today.",
            "chips": ["View invoices", "Record a sale", "Check stock"],
        }

    if time_of_day == "morning" and low_stock_items:
        items_str = ", ".join(low_stock_items[:3])
        return {
            "scenario": "low_stock",
            "text": f"👋 Good morning, {name}. {items_str} {'is' if len(low_stock_items) == 1 else 'are'} running low. You may want to restock before {'it runs' if len(low_stock_items) == 1 else 'they run'} out.",
            "chips": ["Check stock", "Record a sale", "Record an expense"],
        }

    if today_sales > 0 and today_sales > best_day_sales:
        return {
            "scenario": "great_day",
            "text": f"🎉 Good {'afternoon' if time_of_day != 'evening' else 'evening'}, {name}. Congratulations! Today is your best sales day this month. You've already made {_fmt(currency, today_sales)}. Keep it going!",
            "chips": ["Record a sale", "View today's activity", "Create an invoice"],
        }

    if time_of_day == "midday" and yesterday_partial_sales > 0 and today_sales < yesterday_partial_sales * Decimal(str(SLOW_DAY_RATIO)):
        return {
            "scenario": "slow_day",
            "text": f"👋 Good afternoon, {name}. Today has been quieter than usual. Sales are lower than yesterday at this time. Would you like to see what's changed?",
            "chips": ["View today's activity", "Create a report", "Record a sale"],
        }

    if no_activity_today:
        greeting_word = "Good morning" if time_of_day == "morning" else "Good afternoon"
        return {
            "scenario": "no_activity",
            "text": f"👋 {greeting_word}, {name}. I haven't seen any business activity today yet. When you're ready, tell me about your first sale or expense.",
            "chips": ["Record a sale", "Record an expense", "Check stock"],
        }

    if time_of_day == "morning":
        yesterday_sale_count = await _count_transactions(db, business_id, TransactionType.SALE, yesterday_start_utc, today_start_utc)
        low_stock_line = f" You're running low on {low_stock_items[0]}." if low_stock_items else ""
        return {
            "scenario": "morning",
            "text": (
                f"☀️ Good morning, {name}. Yesterday you made {_fmt(currency, yesterday_sales)} from "
                f"{yesterday_sale_count} sale{'s' if yesterday_sale_count != 1 else ''}. Your profit was "
                f"{_fmt(currency, yesterday_sales - yesterday_expenses)}.{low_stock_line} What would you like to do today?"
            ),
            "chips": ["Record a sale", "Check stock", "View yesterday", "Create an invoice"],
        }

    if time_of_day == "midday":
        today_sale_count = await _count_transactions(db, business_id, TransactionType.SALE, today_start_utc, now_utc)
        biggest_category = await _biggest_expense_category(db, business_id, today_start_utc, now_utc)
        expense_line = f" Your biggest expense today is {biggest_category}." if biggest_category else ""
        return {
            "scenario": "midday",
            "text": (
                f"👋 Good afternoon, {name}. So far today you've made {_fmt(currency, today_sales)} from "
                f"{today_sale_count} sale{'s' if today_sale_count != 1 else ''}.{expense_line} How can I help?"
            ),
            "chips": ["Record a sale", "Record an expense", "Create an invoice"],
        }

    return {
        "scenario": "evening",
        "text": f"🌙 Good evening, {name}. Here's how today went. Sales: {_fmt(currency, today_sales)}. Expenses: {_fmt(currency, today_expenses)}. Profit: {_fmt(currency, today_sales - today_expenses)}. Nice work today. What would you like to do before you close?",
        "chips": ["View today's activity", "Create a report", "Check stock"],
    }
