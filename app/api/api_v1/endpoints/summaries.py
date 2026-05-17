from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
from app.api.deps import get_db, get_current_user
from app.models.user import User, PlanType
from app.models.summary import Summary, SummaryType
from pydantic import BaseModel

router = APIRouter()

class SummarySchema(BaseModel):
    id: str
    type: SummaryType
    period_start: datetime
    period_end: datetime
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/latest", response_model=SummarySchema)
async def get_latest_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Summary).where(Summary.user_id == current_user.id).order_by(Summary.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="No summary found")
    
    return summary

@router.get("/daily", response_model=SummarySchema)
async def get_daily_summary(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    stmt = select(Summary).where(
        and_(
            Summary.user_id == current_user.id,
            Summary.type == SummaryType.DAILY,
            Summary.period_start <= dt,
            Summary.period_end >= dt
        )
    )
    result = await db.execute(stmt)
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="No summary found for this date")
    
    return summary

# Similar endpoints for weekly and monthly can be added here
