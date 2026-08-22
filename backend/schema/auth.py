from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator
from pydantic_core.core_schema import ValidationInfo


class CreateUserRegistration(BaseModel):
    """Public sign-up payload."""

    email: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]
    username: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True, min_length=3)]
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: str = Field(..., min_length=8)
    password_confirm: str

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("passwords do not match")
        return value


class CredentialsRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    @classmethod
    def respond(cls, token: str) -> dict:
        return cls(access_token=token).model_dump()


class LoginHistoryOut(BaseModel):
    event_id: str
    user_id: str
    username: str
    ip: str
    success: bool
    user_agent: str
    created_at: datetime


class LoginHistoryList(BaseModel):
    items: list[LoginHistoryOut]


class BlockIpIn(BaseModel):
    ip: str


class BlockedIpOut(BaseModel):
    ip: str


class BlockedIpList(BaseModel):
    items: list[BlockedIpOut]


class ForgotPassword(BaseModel):
    email: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]


class ResetPassword(BaseModel):
    token: str
    email: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]
    password: str = Field(..., min_length=8)
    passwordConfirm: str

    @field_validator("passwordConfirm")
    @classmethod
    def passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("passwords do not match")
        return value
