from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from typing import Optional

class PublicUserResponseModel(BaseModel):
    id: int
    name: str
    phone_number: Optional[int]

class PrivateUserResponseModel(BaseModel):
    id: int
    name: str
    phone_number: Optional[int]
    created_at: datetime
    access_token: str
    is_telegram_user: bool
    telegram_id: Optional[int]

class UpdateUserRequestModel(BaseModel):
    name: str
    phone_number: int