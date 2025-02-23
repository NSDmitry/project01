from __future__ import annotations

from typing import List

from pydantic import BaseModel
from DBmodels import DBBookClub
from services.User.Models import PublicUserResponseModel


class CreateBookClubRequestModel(BaseModel):
    name: str
    description: str

class BookClubResponseModel(BaseModel):
    name: str
    description: str
    owner: PublicUserResponseModel
    members: List[PublicUserResponseModel]

    @classmethod
    def from_db_model(cls, db_model: DBBookClub) -> BookClubResponseModel:
        owner = PublicUserResponseModel.from_db_model(db_model=db_model.owner)
        members = [PublicUserResponseModel.from_db_model(db_model=user) for user in db_model.members]

        return BookClubResponseModel(name=db_model.name, description=db_model.description, owner=owner, members=members)