from __future__ import annotations

from pydantic import BaseModel

class PublicUserResponseModel(BaseModel):
    id: int
    name: str
    phone_number: int

class UpdateUserRequestModel(BaseModel):
    name: str
    phone_number: int