from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from datetime import datetime

from app.core.schemas import ResponseSchema
from app.iam.schemas import UserSummary

class BookClubRelation(str, Enum):
    owner = "owner"
    member = "member"

class GenreResponse(ResponseSchema):
    code: str
    name: str

class CreateBookClubRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=500)
    genres: list[str] = Field(min_length=1, max_length=5)

class UpdateBookClubGenresRequest(BaseModel):
    genres: list[str] = Field(min_length=1, max_length=5)

class BookClubResponse(ResponseSchema):
    id: int
    name: str
    description: str
    created_at: datetime
    owner: Optional[UserSummary] = None
    members_count: int
    threads_count: int
    genres: list[GenreResponse]
