from pydantic import BaseModel, Field
from datetime import date


class ReceiptScanResponse(BaseModel):
    vendor: str = Field("Unknown", description="Shop or company name on the receipt")
    item: str = Field("expense", description="Short description of what was bought")
    amount: float = Field(0.0, description="Total amount paid")
    currency: str = Field("UGX", description="Currency code")
    category: str = Field("Other", description="One of the standard expense categories")
    transaction_date: date = Field(default_factory=date.today, description="Date on the receipt")
    confidence: float = Field(0.0, description="Confidence score from the AI")
