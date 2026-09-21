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
