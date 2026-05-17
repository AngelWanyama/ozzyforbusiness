import json
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.user import User, PlanType
from app.models.transaction import Transaction, TransactionType
from app.models.summary import Summary, SummaryType
from app.core.config import settings
import google.generativeai as genai

class SummaryGenerator:
    def __init__(self):
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

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
        # Fetch transactions for period
        stmt = select(Transaction).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
        result = await db.execute(stmt)
        transactions = result.scalars().all()
        
        if not transactions:
            return # Skip users with no activity
        
        # Calculate totals
        total_sales = sum(t.amount for t in transactions if t.type == TransactionType.SALE)
        total_expenses = sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE)
        sale_count = sum(1 for t in transactions if t.type == TransactionType.SALE)
        
        # Prepare data for AI
        data = {
            "business_name": user.business_name,
            "currency": user.currency,
            "total_sales": float(total_sales),
            "total_expenses": float(total_expenses),
            "sale_count": sale_count,
            "net_profit": float(total_sales - total_expenses),
            "transaction_count": len(transactions),
            "period": summary_type.value
        }
        
        content = await self._get_ai_summary(data)
        
        # Save summary
        summary = Summary(
            user_id=user.id,
            type=summary_type,
            period_start=start_date,
            period_end=end_date,
            content=content
        )
        db.add(summary)
        await db.commit()

    async def _get_ai_summary(self, data: dict) -> str:
        if not self.model:
            return f"You made {data['sale_count']} sales totaling {data['currency']} {data['total_sales']:,}. Your expenses were {data['currency']} {data['total_expenses']:,}. Your profit was {data['currency']} {data['net_profit']:,}."

        prompt = f"""
        You are a business coach for 'Ozzy for Business', helping small business owners in Africa.
        Generate a {data['period']} summary for {data['business_name'] or 'the business'}.
        
        Data:
        - Total Sales: {data['currency']} {data['total_sales']:,} ({data['sale_count']} sales)
        - Total Expenses: {data['currency']} {data['total_expenses']:,}
        - Net Profit: {data['currency']} {data['net_profit']:,}
        
        Write a 2-sentence summary in plain, encouraging language. Mention the profit clearly.
        If it's a daily summary, start with "Today..." or "Yesterday...".
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error calling LLM for summary: {e}")
            return f"You made {data['sale_count']} sales totaling {data['currency']} {data['total_sales']:,}. Profit: {data['currency']} {data['net_profit']:,}."

summary_generator = SummaryGenerator()
