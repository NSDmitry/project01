from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.core.contracts import UserSummary  # noqa: F401 - контракт живёт в core, ре-экспорт для домена
from app.core.schemas import ResponseSchema
from app.core.validators import validate_e164


def validate_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("Имя не может быть пустым")
    if len(name) > 100:
        raise ValueError("Имя должно быть не длиннее 100 символов")
    return name


class SignUpRequest(BaseModel):
    name: str
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)
    _validate_name = field_validator("name")(validate_name)

class SignInRequest(BaseModel):
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class LoginAvailableRequest(BaseModel):
    phone_number: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class TelegramAuthRequest(BaseModel):
    init_data: str

class OwnUserResponse(ResponseSchema):
    id: int
    name: str
    phone_number: Optional[str]
    created_at: datetime
    # None - аватар не загружен.
    avatar_url: Optional[str] = None

class AuthUserResponse(ResponseSchema):
    session_id: str

class LoginAvailableResponse(ResponseSchema):
    is_registered: bool

class UpdateUserRequest(BaseModel):
    name: str
    phone_number: str

    _validate_phone = field_validator("phone_number")(validate_e164)
    _validate_name = field_validator("name")(validate_name)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
