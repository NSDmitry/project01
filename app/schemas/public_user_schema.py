from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

class PublicUserResponseModel(BaseModel):
    id: int
    name: str
    phone_number: int

class PrivateUserResponseModel(BaseModel):
    id: int
    name: str
    phone_number: int | None
    created_at: datetime
    access_token: str
    is_telegram_user: bool
    telegram_id: int | None

class UpdateUserRequestModel(BaseModel):
    name: str
    phone_number: int