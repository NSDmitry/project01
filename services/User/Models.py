from __future__ import annotations

from pydantic import BaseModel

from DBmodels import DBUser


class PublicUserResponseModel(BaseModel):
    id: int
    name: str
    phone_number: int

    @classmethod
    def from_db_model(cls, db_model: DBUser) -> PublicUserResponseModel:
        return PublicUserResponseModel(
            id=db_model.id,
            name=db_model.name,
            phone_number=db_model.phone_number,
        )

class UpdateUserRequestModel(BaseModel):
    name: str
    phone_number: int