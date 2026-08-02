from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.receipt import ReceiptScanResponse
from app.schemas.greeting import GreetingResponse
from app.services.chat_engine import chat_engine
from app.services.receipt_scanner import receipt_scanner
from app.services.greeting_engine import get_greeting
from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()

ALLOWED_RECEIPT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_RECEIPT_BYTES = 8 * 1024 * 1024  # 8MB

@router.post("/process", response_model=ChatResponse)
async def process_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await chat_engine.handle_message(db, current_user, request.text)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan-receipt", response_model=ReceiptScanResponse)
async def scan_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_RECEIPT_TYPES:
        raise HTTPException(status_code=400, detail="Please upload a PNG, JPEG, or WEBP photo of the receipt.")

    contents = await file.read()
    if len(contents) > MAX_RECEIPT_BYTES:
        raise HTTPException(status_code=400, detail="That photo is too large — please use one under 8MB.")

    try:
        result = await receipt_scanner.scan_receipt(contents, file.content_type, user_currency=current_user.currency)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/greeting", response_model=GreetingResponse)
async def get_chat_greeting(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Workers can't see profit/totals, so they get a simple greeting with no figures in it —
    # the full financial greeting engine is owner-only.
    if current_user.role == "worker":
        hour = (datetime.utcnow().hour + 3) % 24  # EAT
        greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
        name = current_user.owner_name or "there"
        return GreetingResponse(
            text=f"👋 {greeting}, {name}! Ready to record today's sales and expenses?",
            chips=["Record a sale", "Record an expense", "Check stock"],
            scenario="worker",
        )

    try:
        result = await get_greeting(db, current_user)
        return GreetingResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))