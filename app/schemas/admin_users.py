from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserGroupEnum


class AdminUserCreateRequest(BaseModel):
    email: EmailStr = Field(examples=["new-user@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["Password1"])
    group: UserGroupEnum = Field(default=UserGroupEnum.USER, examples=["USER"])
    is_active: bool = Field(default=True, examples=[True])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "new-user@example.com",
                "password": "Password1",
                "group": "USER",
                "is_active": True,
            }
        }
    )


class AdminUserResponse(BaseModel):
    message: str = Field(examples=["User created successfully."])
    id: int
    email: EmailStr
    is_active: bool
    group: UserGroupEnum

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "User created successfully.",
                "id": 1,
                "email": "new-user@example.com",
                "is_active": True,
                "group": "USER",
            }
        }
    )
