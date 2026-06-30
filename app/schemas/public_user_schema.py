from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from typing import Optional

from app.schemas.base import ResponseSchema

class UserSummaryModel(ResponseSchema):
    id: int
    name: str

class PublicUserResponseModel(ResponseSchema):
    id: int
    name: str
    phone_number: Optional[int]

class PrivateUserResponseModel(ResponseSchema):
    id: int
    name: str
    phone_number: Optional[int]
    created_at: datetime
    session_id: str
    is_telegram_user: bool
    telegram_id: Optional[int]

class UpdateUserRequestModel(BaseModel):
    name: str
    phone_number: int


class ChangePasswordRequestModel(BaseModel):
    current_password: str
    new_password: str
