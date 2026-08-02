from pydantic import BaseModel
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime
from enum import Enum

class ReportType(str, Enum):
    PNL = "pnl"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"

class TimePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class RevenueBreakdown(BaseModel):
    category: str
    amount: Decimal

class ExpenseBreakdown(BaseModel):
    category: str
    amount: Decimal

class PNLReport(BaseModel):
    total_revenue: Decimal
    revenue_breakdown: List[RevenueBreakdown]
    total_expenses: Decimal
    expense_breakdown: List[ExpenseBreakdown]
    net_profit: Decimal
    currency: str
    start_date: datetime
    end_date: datetime

class AssetBreakdown(BaseModel):
    name: str
    value: Decimal

class LiabilityBreakdown(BaseModel):
    name: str
    value: Decimal

class BalanceSheetReport(BaseModel):
    total_assets: Decimal
    assets_breakdown: List[AssetBreakdown]
    total_liabilities: Decimal
    liabilities_breakdown: List[LiabilityBreakdown]
    equity: Decimal
    currency: str
    as_of_date: datetime

class CashFlowReport(BaseModel):
    cash_in: Decimal
    cash_out: Decimal
    net_cash_flow: Decimal
    currency: str
    start_date: datetime
    end_date: datetime

class AccountingReport(BaseModel):
    report_type: ReportType
    period: TimePeriod
    data: Dict
    summary: str # AI generated plain language summary


class DailyPoint(BaseModel):
    label: str          # e.g. "Mon"
    date: str            # ISO date, e.g. "2026-07-27"
    sales: Decimal
    expenses: Decimal


class CategorySlice(BaseModel):
    category: str
    amount: Decimal
    percent: float


class BestSeller(BaseModel):
    name: str
    units: Decimal
    revenue: Decimal


class ReportDashboard(BaseModel):
    period: str  # "today" | "week" | "month"
    currency: str
    total_sales: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    sales_change_pct: Optional[float] = None
    expenses_change_pct: Optional[float] = None
    daily: List[DailyPoint]
    category_breakdown: List[CategorySlice]
    best_sellers: List[BestSeller]
