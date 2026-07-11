from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.schemas import ResponseSchema


class GenreResponse(ResponseSchema):
    id: int
    code: str
    name: str


class CreateGenreRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0


class UpdateGenreRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0
