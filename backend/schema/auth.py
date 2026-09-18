import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator
from pydantic_core.core_schema import ValidationInfo

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_OTP_CODE = re.compile(r"^\d{6}$")


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
    refresh_token: str | None = None
    token_type: str = "bearer"

    @classmethod
    def respond(cls, access_token: str, refresh_token: str | None = None) -> dict:
        payload = cls(access_token=access_token, refresh_token=refresh_token)
        return payload.model_dump(exclude_none=True)


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


class PhoneStartIn(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def e164(cls, value: str) -> str:
        phone = value.strip().replace(" ", "").replace("-", "")
        if not _E164.match(phone):
            raise ValueError("phone must be E.164 (e.g. +64211234567)")
        return phone


class PhoneConfirmIn(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def six_digits(cls, value: str) -> str:
        code = value.strip()
        if not _OTP_CODE.match(code):
            raise ValueError("code must be 6 digits")
        return code


class VerifyOtpIn(PhoneConfirmIn):
    username: str
    remember_me: bool = False


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
