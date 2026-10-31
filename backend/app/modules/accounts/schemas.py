from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.accounts.models import Role


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(min_length=2, max_length=40)
    accept_terms: bool
    # Honeypot: real people never see/fill this field; bots often do.
    website: str | None = Field(default=None, max_length=200)

    @field_validator("display_name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v or any(ord(c) < 32 for c in v):
            raise ValueError("invalid display name")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    role: Role
    status: str
    email_verified: bool = False
    unit_pref: str
    locale: str
    theme: str


class MeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=40)
    unit_pref: Literal["metric", "imperial"] | None = None
    locale: Literal["en", "es"] | None = None
    theme: Literal["system", "light", "dark"] | None = None


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=10, max_length=200)


class ProRequestIn(BaseModel):
    statement: str = Field(min_length=20, max_length=2000)


class StatusIn(BaseModel):
    status: Literal["probation", "active", "suspended", "banned"]
    reason: str = Field(min_length=3, max_length=500)


class RoleIn(BaseModel):
    role: Role
    reason: str = Field(min_length=3, max_length=500)


class ReviewIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)
