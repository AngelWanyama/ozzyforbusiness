from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class ChatRequest(BaseModel):
    text: str


class ChatDraft(BaseModel):
    type: str  # "sale" | "expense"
    description: str
    amount: float
    quantity: float = 1
    category: Optional[str] = None


class ChatResponse(BaseModel):
    reply: Optional[str] = None
    # "reply" (just show the text) | "confirm_sale" | "confirm_expense" | "need_amount"
    action: str = "reply"
    draft: Optional[ChatDraft] = None
    # Present when a PROPOSE step created a stored proposal awaiting confirmation — the confirm
    # card's Yes button sends this back to /chat/confirm rather than writing anything itself.
    proposal_id: Optional[str] = None


class VoiceChatResponse(ChatResponse):
    transcript: str


class ChatConfirmRequest(BaseModel):
    proposal_id: str


class ChatConfirmResponse(BaseModel):
    ok: bool
    reply: Optional[str] = None
    # Present when confirming one proposal (e.g. "add this new product?") resumes straight into
    # another (the sale it was blocking) rather than just finishing — 2026-09-22 platform-wide
    # button rule, the frontend needs these to show the next confirm card immediately instead of
    # silently dropping it, which is exactly what happened before these fields existed here: this
    # response model previously only declared ok/reply, so FastAPI's response_model filtering
    # silently stripped action/proposal_id/draft off of whatever the service layer returned.
    action: Optional[str] = None
    proposal_id: Optional[str] = None
    draft: Optional[ChatDraft] = None


# --- Onboarding, state-based per Volume 3 of the Brain doc (§3.20) ---

class OnboardingStartRequest(BaseModel):
    local_hour: Optional[int] = None  # entrepreneur's device/browser-local hour (0-23), §3.4


class OnboardingTurnResponse(BaseModel):
    reply: str
    done: bool
    kind: str = "text"  # "text" | "choice" | "logo"
    choices: Optional[List[Dict[str, str]]] = None
    field: Optional[str] = None  # which field this question is about, for the choice/logo UI


class OnboardingMessageRequest(BaseModel):
    text: str


class OnboardingChoiceRequest(BaseModel):
    field: str  # "phone_confirm" | "logo"
    value: str
