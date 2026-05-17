from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional, List
from decimal import Decimal

class ItemBase(BaseModel):
    name: str
    category: Optional[str] = None
    unit_price: Optional[Decimal] = None
    stock_level: Decimal = 0
    is_service: bool = False

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[Decimal] = None
    stock_level: Optional[Decimal] = None
    is_service: Optional[bool] = None

class Item(ItemBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)

class StockAdjustment(BaseModel):
    adjustment_amount: Decimal
    reason: Optional[str] = None
