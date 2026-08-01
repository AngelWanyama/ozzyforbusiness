import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.invite import Invite
from app.schemas.invite import InviteCreate, InviteResponse
from app.core.security import hash_password
from app.core.security import create_access_token

router = APIRouter()


@router.post("/generate", response_model=InviteResponse)
async def generate_invite(
    data: InviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only an owner may create worker invites
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Only the business owner can add workers.")

    # Make a random 6-digit code
    code = f"{random.randint(0, 999999):06d}"

    invite = Invite(
        code=code,
        business_id=current_user.business_id,
        created_by=current_user.id,
        phone_number=data.phone_number,
        used=False,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


class InviteRedeem(BaseModel):
    code: str
    password: str


class InviteCheck(BaseModel):
    code: str


@router.post("/check")
async def check_invite(data: InviteCheck, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invite).where(Invite.code == data.code))
    invite = result.scalars().first()
    if not invite:
        raise HTTPException(status_code=404, detail="That code doesn't exist. Please check it and try again.")
    if invite.used:
        raise HTTPException(status_code=400, detail="That code has already been used.")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="That code has expired. Ask the owner for a new one.")
    return {"valid": True, "phone_number": invite.phone_number}


@router.post("/redeem")
async def redeem_invite(data: InviteRedeem, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invite).where(Invite.code == data.code))
    invite = result.scalars().first()
    if not invite:
        raise HTTPException(status_code=404, detail="That code doesn't exist. Please check it and try again.")
    if invite.used:
        raise HTTPException(status_code=400, detail="That code has already been used.")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="That code has expired. Ask the owner for a new one.")

    if not invite.phone_number:
        raise HTTPException(status_code=400, detail="This invite has no phone number attached. Ask the owner to create a new one with your number.")

    # Make sure this phone isn't already registered
    existing = await db.execute(select(User).where(User.phone_number == invite.phone_number))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="An account with this phone number already exists.")

    # Create the worker, joined to the owner's business
    worker = User(
        phone_number=invite.phone_number,
        password_hash=hash_password(data.password),
        role="worker",
        business_id=invite.business_id,
    )
    db.add(worker)
    invite.used = True
    await db.commit()
    await db.refresh(worker)

    token = create_access_token(str(worker.id))
    return {"access_token": token, "token_type": "bearer"}
