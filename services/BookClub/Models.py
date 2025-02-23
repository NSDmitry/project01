from pydantic import BaseModel

from DBmodels import DBBookClub
from services.User.Models import PublicUserResponseModel
from typing import List


class CreateBookClubRequestModel(BaseModel):
    name: str
    description: str

class BookClubResponseModel(BaseModel):
    name: str
    description: str
    owner_id: int

    @classmethod
    def from_db_model(cls, db_model: DBBookClub) -> PublicUserResponseModel:
        return BookClubResponseModel(name=db_model.name, description=db_model.description, owner_id=db_model.owner_id)