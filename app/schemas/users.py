from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models import GenderEnum


class UserProfileRead(BaseModel):
    first_name: str | None = Field(default=None, examples=["Ada"])
    last_name: str | None = Field(default=None, examples=["Lovelace"])
    avatar: str | None = Field(
        default=None,
        examples=["http://localhost:9000/online-cinema/avatars/1/avatar.jpg"],
    )
    gender: GenderEnum | None = Field(default=None, examples=["WOMAN"])
    date_of_birth: date | None = Field(default=None, examples=["1995-05-12"])
    info: str | None = Field(default=None, examples=["Cinema fan."])

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100, examples=["Ada"])
    last_name: str | None = Field(default=None, max_length=100, examples=["Lovelace"])
    gender: GenderEnum | None = Field(default=None, examples=["WOMAN"])
    date_of_birth: date | None = Field(default=None, examples=["1995-05-12"])
    info: str | None = Field(default=None, examples=["Cinema fan."])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "gender": "WOMAN",
                "date_of_birth": "1995-05-12",
                "info": "Cinema fan.",
            }
        }
    )
