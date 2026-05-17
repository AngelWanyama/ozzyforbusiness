from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models.transaction import TransactionType

class TransactionBase(BaseModel):
    type: TransactionType
    amount: Decimal
    currency: str = "UGX"
    item_id: Optional[UUID] = None
    description: Optional[str] = None
    quantity: Decimal = 1.0
    transaction_date: Optional[datetime] = None

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: UUID
    user_id: UUID
    transaction_date: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionHistory(BaseModel):
    total: int
    items: List[Transaction]

class SummaryReport(BaseModel):
    total_sales: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    currency: str = "UGX"
