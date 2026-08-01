from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.api.deps import get_db
from app.models.otp import OTP as OTPModel
from app.models.user import User as UserModel
from app.schemas.auth import OTPRequest, OTPVerify, RegisterRequest, LoginRequest
from app.schemas.token import Token
from app.core.security import create_access_token, hash_password, verify_password
from datetime import datetime, timedelta
import random
import uuid

router = APIRouter()

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    *,
    db: AsyncSession = Depends(get_db),
    register_in: RegisterRequest
):
    # Check if this phone number is already registered
    stmt = select(UserModel).where(UserModel.phone_number == register_in.phone_number)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user and existing_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this phone number already exists. Please log in instead."
        )

    if existing_user:
        # User exists from old OTP flow but has no password yet — set one now
        existing_user.password_hash = hash_password(register_in.password)
        user = existing_user
    else:
        new_id = uuid.uuid4()
        user = UserModel(
            id=new_id,
            phone_number=register_in.phone_number,
            password_hash=hash_password(register_in.password),
            currency="UGX",
            role="owner",
            business_id=new_id,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(
    *,
    db: AsyncSession = Depends(get_db),
    login_in: LoginRequest
):
    stmt = select(UserModel).where(UserModel.phone_number == login_in.phone_number)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.password_hash or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password"
        )

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(
    *,
    db: AsyncSession = Depends(get_db),
    otp_in: OTPRequest
):
    # Generate 6-digit OTP
    code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Delete any existing OTPs for this phone number
    await db.execute(delete(OTPModel).where(OTPModel.phone_number == otp_in.phone_number))
    
    # Save OTP
    otp = OTPModel(
        phone_number=otp_in.phone_number,
        code=code,
        expires_at=expires_at
    )
    db.add(otp)
    await db.commit()
    
    # Mock SMS sending
    print(f"DEBUG: Sending OTP {code} to {otp_in.phone_number}")
    
    return {"message": "OTP sent successfully", "debug_code": code}

@router.post("/otp/verify", response_model=Token)
async def verify_otp(
    *,
    db: AsyncSession = Depends(get_db),
    otp_verify: OTPVerify
):
    # Find the OTP
    stmt = select(OTPModel).where(
        OTPModel.phone_number == otp_verify.phone_number,
        OTPModel.code == otp_verify.code
    )
    result = await db.execute(stmt)
    otp = result.scalars().first()
    
    if not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code"
        )
    
    if otp.is_expired():
        await db.delete(otp)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code expired"
        )
    
    # Correct OTP, find or create user
    stmt = select(UserModel).where(UserModel.phone_number == otp_verify.phone_number)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        user = UserModel(
            id=uuid.uuid4(),
            phone_number=otp_verify.phone_number,
            currency="UGX"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Generate JWT
    access_token = create_access_token(subject=user.id)
    
    # Cleanup OTP
    await db.delete(otp)
    await db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }