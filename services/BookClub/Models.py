from __future__ import annotations

from typing import List

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
    owner: PublicUserResponseModel
    members: List[PublicUserResponseModel]

    @classmethod
    def from_db_model(cls, db_model: DBBookClub) -> BookClubResponseModel:
        owner = PublicUserResponseModel.from_db_model(db_model=db_model.owner)
        members = [PublicUserResponseModel.from_db_model(db_model=user) for user in db_model.members]

        return BookClubResponseModel(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            creation_date=db_model.creation_date,
            owner=owner,
            members=members
        )

class DeleteBookClubResponse(BaseModel):
    message: str