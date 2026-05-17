from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class NLPTransactionResponse(BaseModel):
    intent: str = Field(..., description="One of 'sale', 'expense', 'inventory', or 'query'")
    amount: float = Field(0.0, description="The monetary value of the transaction")
    item: str = Field("unknown", description="The item or service involved")
    quantity: float = Field(1.0, description="The quantity of the item")
    currency: str = Field("UGX", description="The currency code")
    transaction_date: date = Field(default_factory=date.today, description="The date of the transaction")
    confidence: float = Field(0.0, description="Confidence score from the LLM")
