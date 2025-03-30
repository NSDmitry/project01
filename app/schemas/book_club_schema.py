from __future__ import annotations

from typing import List

from pydantic import BaseModel
from datetime import datetime

class CreateBookClubRequestModel(BaseModel):
    name: str
    description: str

class BookClubResponseModel(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    owner_id: int
    members_ids: List[int]