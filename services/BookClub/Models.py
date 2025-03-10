from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime

from DBmodels import DBBookClub
from services.User.Models import PublicUserResponseModel


class CreateBookClubRequestModel(BaseModel):
    name: str
    description: str

class BookClubResponseModel(BaseModel):
    id: int
    name: str
    description: str
    creation_date: datetime
    owner_id: int

    @classmethod
    def from_db_model(cls, db_model: DBBookClub) -> BookClubResponseModel:
        return BookClubResponseModel(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            creation_date=db_model.creation_date,
            owner_id=db_model.owner_id,
        )

class DeleteBookClubResponse(BaseModel):
    message: str