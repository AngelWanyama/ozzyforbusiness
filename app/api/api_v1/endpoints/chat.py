from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.chat import (
    ChatRequest, ChatResponse, VoiceChatResponse, ChatConfirmRequest, ChatConfirmResponse,
    OnboardingTurnResponse, OnboardingMessageRequest, OnboardingChoiceRequest,
)
from app.schemas.receipt import ReceiptScanResponse
from app.schemas.greeting import GreetingResponse
from app.services.chat_engine import chat_engine
from app.services.ai_client import ai_client
from app.services import onboarding_engine as ob
from app.services.receipt_scanner import receipt_scanner
from app.services.greeting_engine import get_greeting
from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()

ALLOWED_RECEIPT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_RECEIPT_BYTES = 8 * 1024 * 1024  # 8MB

ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/mpeg"}
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB — plenty for a short voice message
MIN_AUDIO_BYTES = 800  # anything smaller is essentially silence/an empty recording

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


@router.post("/confirm", response_model=ChatConfirmResponse)
async def confirm_chat_proposal(
    request: ChatConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backs the confirm card's Yes button — an explicit confirmation of a specific stored
    proposal, checked in application code (not inferred by the model) before anything is
    written, per Appendix A's PROPOSE/COMMIT state machine."""
    try:
        result = await chat_engine.confirm_proposal_by_id(db, current_user, request.proposal_id)
        return ChatConfirmResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel", response_model=ChatConfirmResponse)
async def cancel_chat_proposal(
    request: ChatConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backs the confirm card's No button (2026-09-22 platform-wide button rule) — every yes/no
    proposal gets an explicit cancel path here, not just a typed 'no'."""
    try:
        result = await chat_engine.cancel_proposal_by_id(db, current_user, request.proposal_id)
        return ChatConfirmResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/onboarding-start", response_model=OnboardingTurnResponse)
async def onboarding_start(
    local_hour: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """§3.3/§3.4: the opening greeting (time-based, never asks for a timezone), or §3.21's
    resume message if this entrepreneur already has onboarding facts saved from a previous
    session that never finished."""
    state = current_user.onboarding_state or {}
    if state.get("known"):
        nxt = ob.next_missing_field(state)
        if nxt is None:
            return OnboardingTurnResponse(reply=ob.completion_message(state), done=True)
        q = ob.question_for(nxt, state, current_user)
        reply = f"{ob.resume_message(state)}\n\n{q['text']}"
        return OnboardingTurnResponse(reply=reply, done=False, kind=q["kind"], choices=q.get("choices"), field=nxt)
    return OnboardingTurnResponse(reply=ob.opening_greeting(local_hour), done=False, kind="text", field="owner_name")


@router.post("/onboarding-message", response_model=OnboardingTurnResponse)
async def onboarding_message(
    request: OnboardingMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Every free-text onboarding turn — real model interpretation extracting every fact the
    message contains (§3.7, §3.20), never just the one field that was last asked about."""
    state = current_user.onboarding_state or {}
    try:
        captured = ob.handle_awaiting_capture(current_user, state, request.text)
        result = captured if captured is not None else await ob.interpret_onboarding_message(current_user, state, request.text)
        current_user.onboarding_state = result["state"]
        if result["done"]:
            await ob.finalize_onboarding(db, current_user, result["state"])
        else:
            await db.commit()
        return OnboardingTurnResponse(
            reply=result["reply"], done=result["done"], kind=result.get("kind", "text"),
            choices=result.get("choices"), field=result.get("next_field"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding-choice", response_model=OnboardingTurnResponse)
async def onboarding_choice(
    request: OnboardingChoiceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """§3.9 (phone) and §3.11 (logo) — the two places a button earns its place per Volume 2,
    handled deterministically, no model call."""
    state = current_user.onboarding_state or {}
    try:
        result = ob.handle_onboarding_choice(current_user, state, request.field, request.value)
        current_user.onboarding_state = result["state"]
        if result["done"]:
            await ob.finalize_onboarding(db, current_user, result["state"])
        else:
            await db.commit()
        return OnboardingTurnResponse(
            reply=result["reply"], done=result["done"], kind=result.get("kind", "text"),
            choices=result.get("choices"), field=result.get("next_field"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice", response_model=VoiceChatResponse)
async def process_voice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = (file.content_type or "").split(";")[0].strip()
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="That recording format isn't supported. Please try again.")

    contents = await file.read()
    if len(contents) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="That recording is too long. Please keep it under a minute or so.")
    if len(contents) < MIN_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="I didn't catch any audio there. Please try recording again.")

    transcript = ai_client.transcribe_audio(contents, filename=file.filename or "recording.webm")
    if not transcript:
        raise HTTPException(status_code=400, detail="I couldn't hear that clearly. Please try again, ideally somewhere a bit quieter.")

    try:
        result = await chat_engine.handle_message(db, current_user, transcript)
        return VoiceChatResponse(transcript=transcript, **result)
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