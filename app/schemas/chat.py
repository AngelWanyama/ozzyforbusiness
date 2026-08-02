from pydantic import BaseModel
from typing import Optional


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


class VoiceChatResponse(ChatResponse):
    transcript: str
