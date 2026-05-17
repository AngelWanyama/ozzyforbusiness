from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.item import Item as ItemModel
from app.schemas.item import Item, ItemCreate, ItemUpdate, StockAdjustment
import uuid

router = APIRouter()

@router.get("/", response_model=List[Item])
async def read_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    stmt = select(ItemModel).where(ItemModel.user_id == current_user.id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=Item)
async def create_item(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    item_in: ItemCreate
):
    item = ItemModel(
        **item_in.model_dump(),
        user_id=current_user.id
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.get("/{item_id}", response_model=Item)
async def read_item(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    item_id: uuid.UUID
):
    stmt = select(ItemModel).where(ItemModel.id == item_id, ItemModel.user_id == current_user.id)
    result = await db.execute(stmt)
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=Item)
async def update_item(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    item_id: uuid.UUID,
    item_in: ItemUpdate
):
    stmt = select(ItemModel).where(ItemModel.id == item_id, ItemModel.user_id == current_user.id)
    result = await db.execute(stmt)
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.post("/{item_id}/adjust-stock", response_model=Item)
async def adjust_stock(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    item_id: uuid.UUID,
    adjustment: StockAdjustment
):
    stmt = select(ItemModel).where(ItemModel.id == item_id, ItemModel.user_id == current_user.id)
    result = await db.execute(stmt)
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.stock_level += adjustment.adjustment_amount
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
