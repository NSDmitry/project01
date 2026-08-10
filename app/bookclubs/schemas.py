from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from datetime import datetime

from app.core.contracts import GenreResponse, UserSummary
from app.core.params import MAX_OFFSET
from app.core.schemas import ResponseSchema

class BookClubRelation(str, Enum):
    owner = "owner"
    member = "member"

class CreateBookClubRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=500)
    genres: list[str] = Field(max_length=5)

class UpdateBookClubRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, min_length=3, max_length=500)

class UpdateBookClubGenresRequest(BaseModel):
    genres: list[str] = Field(max_length=5)

class SearchBookClubsRequest(BaseModel):
    query: Optional[str] = None
    relation: Optional[BookClubRelation] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0, le=MAX_OFFSET)

class BookClubResponse(ResponseSchema):
    id: int
    name: str
    description: str
    created_at: datetime
    owner: Optional[UserSummary] = None
    members_count: int = 0
    threads_count: int = 0
    genres: list[GenreResponse] = []
