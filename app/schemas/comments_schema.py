from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import ResponseSchema
from app.schemas.public_user_schema import UserSummary


class CommentResponse(ResponseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    content: str
    thread_id: int
    author: Optional[UserSummary] = None

class CommentCreateRequest(BaseModel):
    content: str

class CommentUpdateRequest(BaseModel):
    content: str
