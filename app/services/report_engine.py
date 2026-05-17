import json
import io
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.config import settings
from app.models.transaction import Transaction, TransactionType
from app.models.item import Item
from app.models.user import User
from app.schemas.report import (
    ReportType, TimePeriod, PNLReport, BalanceSheetReport, 
    CashFlowReport, AccountingReport, RevenueBreakdown, 
    ExpenseBreakdown, AssetBreakdown, LiabilityBreakdown
)
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch

class ReportEngineService:
    def __init__(self):
        # Configure Gemini
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    async def get_pnl_report(
        self, db: AsyncSession, user: User, start_date: datetime, end_date: datetime
    ) -> PNLReport:
        # Get Revenue
        revenue_stmt = select(Transaction.amount, Transaction.description).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.SALE,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
        revenue_result = await db.execute(revenue_stmt)
        revenue_items = revenue_result.all()
        total_revenue = sum([item.amount for item in revenue_items]) if revenue_items else Decimal(0)

        # Revenue Breakdown (by item name/description for now)
        revenue_map = {}
        for item in revenue_items:
            desc = item.description or "General Sale"
            revenue_map[desc] = revenue_map.get(desc, Decimal(0)) + item.amount
        
        revenue_breakdown = [
            RevenueBreakdown(category=k, amount=v) for k, v in revenue_map.items()
        ]

        # Get Expenses
        expense_stmt = select(Transaction.amount, Transaction.description).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
        expense_result = await db.execute(expense_stmt)
        expense_items = expense_result.all()
        total_expenses = sum([item.amount for item in expense_items]) if expense_items else Decimal(0)

        # Expense Breakdown
        expense_map = {}
        for item in expense_items:
            desc = item.description or "General Expense"
            expense_map[desc] = expense_map.get(desc, Decimal(0)) + item.amount
        
        expense_breakdown = [
            ExpenseBreakdown(category=k, amount=v) for k, v in expense_map.items()
        ]

        return PNLReport(
            total_revenue=total_revenue,
            revenue_breakdown=revenue_breakdown,
            total_expenses=total_expenses,
            expense_breakdown=expense_breakdown,
            net_profit=total_revenue - total_expenses,
            currency=user.currency,
            start_date=start_date,
            end_date=end_date
        )

    async def get_balance_sheet_report(
        self, db: AsyncSession, user: User, as_of_date: datetime
    ) -> BalanceSheetReport:
        # Cash on hand (calculated from all transactions up to date)
        sales_stmt = select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.SALE,
                Transaction.transaction_date <= as_of_date
            )
        )
        expenses_stmt = select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date <= as_of_date
            )
        )
        
        sales_res = await db.execute(sales_stmt)
        expenses_res = await db.execute(expenses_stmt)
        
        total_sales = sales_res.scalar() or Decimal(0)
        total_expenses = expenses_res.scalar() or Decimal(0)
        cash_on_hand = total_sales - total_expenses

        # Inventory Value
        items_stmt = select(Item).where(Item.user_id == user.id)
        items_res = await db.execute(items_stmt)
        items = items_res.scalars().all()
        
        inventory_value = Decimal(0)
        for item in items:
            if item.stock_level and item.unit_price:
                inventory_value += item.stock_level * item.unit_price

        assets_breakdown = [
            AssetBreakdown(name="Cash on Hand", value=cash_on_hand),
            AssetBreakdown(name="Inventory Value", value=inventory_value)
        ]
        total_assets = cash_on_hand + inventory_value

        # For now, liabilities are 0 unless we add a debt model
        liabilities_breakdown = []
        total_liabilities = Decimal(0)

        return BalanceSheetReport(
            total_assets=total_assets,
            assets_breakdown=assets_breakdown,
            total_liabilities=total_liabilities,
            liabilities_breakdown=liabilities_breakdown,
            equity=total_assets - total_liabilities,
            currency=user.currency,
            as_of_date=as_of_date
        )

    async def get_cash_flow_report(
        self, db: AsyncSession, user: User, start_date: datetime, end_date: datetime
    ) -> CashFlowReport:
        # Cash In (Sales)
        cash_in_stmt = select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.SALE,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
        cash_in_res = await db.execute(cash_in_stmt)
        cash_in = cash_in_res.scalar() or Decimal(0)

        # Cash Out (Expenses)
        cash_out_stmt = select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )
        cash_out_res = await db.execute(cash_out_stmt)
        cash_out = cash_out_res.scalar() or Decimal(0)

        return CashFlowReport(
            cash_in=cash_in,
            cash_out=cash_out,
            net_cash_flow=cash_in - cash_out,
            currency=user.currency,
            start_date=start_date,
            end_date=end_date
        )

    async def generate_ai_summary(self, report_type: ReportType, data: Dict, user_name: str) -> str:
        if not self.model:
            return "AI summary is not available at the moment. Please configure the GEMINI_API_KEY."

        prompt = f"""
        You are a financial advisor for 'Ozzy for Business', helping small business owners in Africa understand their financial reports.
        
        Business Owner: {user_name}
        Report Type: {report_type.value}
        Report Data: {json.dumps(data, default=str)}
        
        Provide a 2-3 sentence summary of this report in plain, encouraging language. 
        Focus on the most important takeaway (e.g., profit growth, high expenses, or stock value).
        Mention the specific currency used in the data.
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating AI summary: {e}")
            return "Unable to generate AI summary at this time."

    def export_to_pdf(self, report_type: ReportType, data: Dict, summary: str, user: User) -> bytes:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(1 * inch, height - 1 * inch, f"{user.business_name or 'My Business'} - {report_type.value.replace('_', ' ').title()}")
        
        c.setFont("Helvetica", 12)
        c.drawString(1 * inch, height - 1.25 * inch, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.drawString(1 * inch, height - 1.45 * inch, f"Currency: {user.currency}")

        # Summary Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(1 * inch, height - 2 * inch, "AI Summary")
        c.setFont("Helvetica-Oblique", 11)
        
        # Wrap summary text
        text_object = c.beginText(1 * inch, height - 2.2 * inch)
        text_object.setFont("Helvetica-Oblique", 11)
        lines = self._wrap_text(summary, 80)
        for line in lines:
            text_object.textLine(line)
        c.drawText(text_object)

        # Data Section
        y_pos = height - 3.5 * inch
        c.setFont("Helvetica-Bold", 14)
        c.drawString(1 * inch, y_pos, "Financial Details")
        y_pos -= 0.3 * inch
        c.setFont("Helvetica", 11)

        for key, value in data.items():
            if isinstance(value, list):
                c.setFont("Helvetica-Bold", 11)
                c.drawString(1.2 * inch, y_pos, f"{key.replace('_', ' ').title()}:")
                y_pos -= 0.2 * inch
                c.setFont("Helvetica", 11)
                for item in value:
                    if isinstance(item, dict):
                        item_str = " | ".join([f"{k}: {v}" for k, v in item.items()])
                        c.drawString(1.4 * inch, y_pos, f"- {item_str}")
                        y_pos -= 0.2 * inch
            else:
                c.drawString(1.2 * inch, y_pos, f"{key.replace('_', ' ').title()}: {value}")
                y_pos -= 0.2 * inch
            
            if y_pos < 1 * inch:
                c.showPage()
                y_pos = height - 1 * inch

        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _wrap_text(self, text: str, width: int) -> List[str]:
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        lines.append(" ".join(current_line))
        return lines

report_engine = ReportEngineService()
