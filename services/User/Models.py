from __future__ import annotations

from pydantic import BaseModel

from DBmodels import DBUser


class PublicUserResponseModel(BaseModel):
    id: int
    name: str
    phone_number: int
    owned_book_clubs_ids: list[int]
    joined_book_clubs_ids: list[int]

    @classmethod
    def from_db_model(cls, db_model: DBUser) -> PublicUserResponseModel:
        return PublicUserResponseModel(
            id=db_model.id,
            name=db_model.name,
            phone_number=db_model.phone_number,
            owned_book_clubs_ids= [club.id for club in db_model.owned_clubs],
            joined_book_clubs_ids = [club.id for club in db_model.book_clubs]
        )

class UpdateUserRequestModel(BaseModel):
    name: str
    phone_number: int