from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field
from datetime import datetime

from app.schemas.base import ResponseSchema
from app.schemas.public_user_schema import UserSummaryModel

class BookClubRelation(str, Enum):
    owner = "owner"
    member = "member"

class CreateBookClubRequestModel(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=500)

class BookClubResponseModel(ResponseSchema):
    id: int
    name: str
    description: str
    created_at: datetime
    owner: UserSummaryModel
    members_count: int
    threads_count: int