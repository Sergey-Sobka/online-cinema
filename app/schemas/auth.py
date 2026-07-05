from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ResendActivationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str
