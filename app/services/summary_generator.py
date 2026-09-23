import json
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.user import User, PlanType
from app.models.transaction import Transaction, TransactionType
from app.models.summary import Summary, SummaryType
from app.services.ai_client import ai_client

class SummaryGenerator:
    async def generate_daily_summaries(self, db: AsyncSession):
        # Generate summaries for yesterday
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        start_of_day = datetime.combine(yesterday, datetime.min.time())
        end_of_day = datetime.combine(yesterday, datetime.max.time())
        
        # Get all active users
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        for user in users:
            await self._generate_user_summary(db, user, SummaryType.DAILY, start_of_day, end_of_day)

    async def generate_weekly_summaries(self, db: AsyncSession):
        # Generate summaries for last week
        today = datetime.utcnow().date()
        start_of_week = today - timedelta(days=today.weekday() + 7) # Start of last week (Monday)
        end_of_week = start_of_week + timedelta(days=6) # End of last week (Sunday)
        
        start_dt = datetime.combine(start_of_week, datetime.min.time())
        end_dt = datetime.combine(end_of_week, datetime.max.time())
        
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        for user in users:
            await self._generate_user_summary(db, user, SummaryType.WEEKLY, start_dt, end_dt)

    async def generate_monthly_summaries(self, db: AsyncSession):
        # Generate summaries for last month
        today = datetime.utcnow().date()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        
        start_dt = datetime.combine(first_day_last_month, datetime.min.time())
        end_dt = datetime.combine(last_day_last_month, datetime.max.time())
        
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        for user in users:
            await self._generate_user_summary(db, user, SummaryType.MONTHLY, start_dt, end_dt)

    async def _generate_user_summary(
        self, db: AsyncSession, user: User, summary_type: SummaryType, start_date: datetime, end_date: datetime
    ):
        # Fetch transactions for period (shared across the whole business, not just
        # this individual user - fixes the siloing bug where a worker's sales never
        # reached the owner's totals). Fall back to the user's own id if they
        # somehow have no business_id yet (should not happen post Stage A backfill).
        effective_business_id = user.business_id or user.id
        stmt = select(Transaction).where(
            and_(
                Transaction.business_id == effective_business_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
        result = await db.execute(stmt)
        transactions = result.scalars().all()
        
        if not transactions:
            return # Skip users with no activity
        
        # Calculate totals. net_profit subtracts cost of goods sold, not just expenses -- see
        # app/services/financials.py for why (confirmed 2026-09-23: it wasn't being subtracted
        # anywhere in the app, overstating profit for every sale of a priced product).
        sales = [t for t in transactions if t.type == TransactionType.SALE]
        total_sales = sum(t.amount for t in sales)
        total_expenses = sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE)
        cost_of_goods = sum((t.cost_of_goods or 0) for t in sales)
        cogs_known_complete = all(t.cost_of_goods is not None and t.cost_of_goods_complete is not False for t in sales)
        sale_count = len(sales)

        # Prepare data for AI
        data = {
            "business_name": user.business_name,
            "currency": user.currency,
            "total_sales": float(total_sales),
            "total_expenses": float(total_expenses),
            "cost_of_goods_sold": float(cost_of_goods),
            "sale_count": sale_count,
            "net_profit": float(total_sales - cost_of_goods - total_expenses),
            "cogs_known_complete": cogs_known_complete,
            "transaction_count": len(transactions),
            "period": summary_type.value
        }
        
        content = await self._get_ai_summary(data)
        
        # Save summary
        summary = Summary(
            user_id=user.id,
            business_id=user.business_id or user.id,
            type=summary_type,
            period_start=start_date,
            period_end=end_date,
            content=content
        )
        db.add(summary)
        await db.commit()

    async def _get_ai_summary(self, data: dict) -> str:
        caveat = "" if data.get("cogs_known_complete", True) else " (some sold items don't have a buying price on file yet, so actual profit may be a bit lower)"
        fallback = (
            f"You made {data['sale_count']} sales totaling {data['currency']} {data['total_sales']:,}. "
            f"Your expenses were {data['currency']} {data['total_expenses']:,}. "
            f"Your profit was {data['currency']} {data['net_profit']:,}.{caveat}"
        )
        if not ai_client.is_available:
            return fallback

        cogs_note = "" if data.get("cogs_known_complete", True) else "\n        - Note: some sold items have no buying price on file, so mention plainly that real profit could be a bit lower than this figure, don't state it as exact."
        prompt = f"""
        You are a business coach for 'Ozzy for Business', helping small business owners in Africa.
        Generate a {data['period']} summary for {data['business_name'] or 'the business'}.

        Data:
        - Total Sales: {data['currency']} {data['total_sales']:,} ({data['sale_count']} sales)
        - Cost of Goods Sold: {data['currency']} {data.get('cost_of_goods_sold', 0):,}
        - Total Expenses: {data['currency']} {data['total_expenses']:,}
        - Net Profit: {data['currency']} {data['net_profit']:,}{cogs_note}

        Write a 2-sentence summary in plain, encouraging language. Mention the profit clearly.
        If it's a daily summary, start with "Today..." or "Yesterday...".
        """

        result = ai_client.generate(prompt)
        return result if result is not None else fallback

summary_generator = SummaryGenerator()