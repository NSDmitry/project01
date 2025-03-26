from __future__ import annotations

from typing import List

from pydantic import BaseModel
from datetime import datetime

from app.db.models.db_book_club import DBBookClub

class CreateBookClubRequestModel(BaseModel):
    name: str
    description: str

class BookClubResponseModel(BaseModel):
    id: int
    name: str
    description: str
    creation_date: datetime
    owner_id: int
    members_ids: List[int]

    @classmethod
    def from_db_model(cls, db_model: DBBookClub) -> BookClubResponseModel:
        return BookClubResponseModel(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            creation_date=db_model.creation_date,
            owner_id=db_model.owner_id,
            members_ids=db_model.members_ids
        )

class DeleteBookClubResponse(BaseModel):
    message: str