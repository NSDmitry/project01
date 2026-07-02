from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import ResponseSchema
from app.schemas.public_user_schema import UserSummaryModel


class CommentResponseModel(ResponseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    content: str
    thread_id: int
    author: Optional[UserSummaryModel] = None

class CommentCreateRequestModel(BaseModel):
    content: str

class CommentUpdateRequestModel(BaseModel):
    content: str
