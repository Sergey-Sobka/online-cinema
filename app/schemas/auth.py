from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["Password1"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "user@example.com", "password": "Password1"}
        }
    )


class ResendActivationRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com"}}
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(examples=["Password1"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "user@example.com", "password": "Password1"}
        }
    )


class TokenPairResponse(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    refresh_token: str = Field(examples=["JjP2p8fNQp4O5kE6iQbD5g"])
    token_type: str = Field(default="bearer", examples=["bearer"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "JjP2p8fNQp4O5kE6iQbD5g",
                "token_type": "bearer",
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1, examples=["JjP2p8fNQp4O5kE6iQbD5g"])

    model_config = ConfigDict(
        json_schema_extra={"example": {"refresh_token": "JjP2p8fNQp4O5kE6iQbD5g"}}
    )


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1, examples=["JjP2p8fNQp4O5kE6iQbD5g"])

    model_config = ConfigDict(
        json_schema_extra={"example": {"refresh_token": "JjP2p8fNQp4O5kE6iQbD5g"}}
    )


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(examples=["Password1"])
    new_password: str = Field(
        min_length=8,
        max_length=128,
        examples=["NewPassword1"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "old_password": "Password1",
                "new_password": "NewPassword1",
            }
        }
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com"}}
    )


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, examples=["reset-token"])
    new_password: str = Field(
        min_length=8,
        max_length=128,
        examples=["ResetPassword1"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "reset-token",
                "new_password": "ResetPassword1",
            }
        }
    )


class MessageResponse(BaseModel):
    message: str = Field(examples=["Operation completed successfully."])

    model_config = ConfigDict(
        json_schema_extra={"example": {"message": "Operation completed successfully."}}
    )
