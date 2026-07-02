from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from typing import Optional

from app.core.validators import validate_e164
from app.schemas.base import ResponseSchema

class UserSummaryModel(ResponseSchema):
    id: int
    name: str

class OwnUserResponseModel(ResponseSchema):
    id: int
    name: str
    phone_number: Optional[str]
    created_at: datetime

class AuthUserResponseModel(ResponseSchema):
    session_id: str

class UpdateUserRequestModel(BaseModel):
    name: str
    phone_number: str

    _validate_phone = field_validator("phone_number")(validate_e164)


class ChangePasswordRequestModel(BaseModel):
    current_password: str
    new_password: str
