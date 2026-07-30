from pydantic import BaseModel, Field

class OTPRequest(BaseModel):
    phone_number: str = Field(..., example="+256700000000")

class OTPVerify(BaseModel):
    phone_number: str = Field(..., example="+256700000000")
    code: str = Field(..., example="123456")

class RegisterRequest(BaseModel):
    phone_number: str = Field(..., example="+256700000000")
    password: str = Field(..., min_length=6, example="mypassword123")

class LoginRequest(BaseModel):
    phone_number: str = Field(..., example="+256700000000")
    password: str = Field(..., example="mypassword123")