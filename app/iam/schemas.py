from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.core.schemas import ResponseSchema
from app.core.validators import validate_e164


class SignUpRequest(BaseModel):
    name: str
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class SignInRequest(BaseModel):
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class TelegramAuthRequest(BaseModel):
    init_data: str

class UserSummary(ResponseSchema):
    id: int
    name: str

class OwnUserResponse(ResponseSchema):
    id: int
    name: str
    phone_number: Optional[str]
    created_at: datetime

class AuthUserResponse(ResponseSchema):
    session_id: str

class UpdateUserRequest(BaseModel):
    name: str
    phone_number: str

    _validate_phone = field_validator("phone_number")(validate_e164)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
