from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import ResponseSchema


class DisscussionResponseModel(ResponseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    title: str
    content: str
    club_id: int
    author_id: int

class DiscussionCreateRequestModel(BaseModel):
    title: str
    content: str
    club_id: int

class DiscussionUpdateRequestModel(BaseModel):
    title: str
    content: str