from pydantic import BaseModel, Field

class OTPRequest(BaseModel):
    phone_number: str = Field(..., example="+256700000000")

class OTPVerify(BaseModel):
    phone_number: str = Field(..., example="+256700000000")
    code: str = Field(..., example="123456")
