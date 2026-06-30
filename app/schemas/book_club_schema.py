from __future__ import annotations

from typing import List

from pydantic import BaseModel
from datetime import datetime

from app.schemas.base import ResponseSchema

class CreateBookClubRequestModel(BaseModel):
    name: str
    description: str

class BookClubResponseModel(ResponseSchema):
    id: int
    name: str
    description: str
    created_at: datetime
    owner_id: int
    members_ids: List[int]