from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.books.schemas import BookResponse
from app.core.schemas import ResponseSchema
from app.iam.schemas import UserSummary


class ThreadResponse(ResponseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    title: str
    content: str
    club_id: int
    author: Optional[UserSummary] = None
    book: Optional[BookResponse] = None

class ThreadCreateRequest(BaseModel):
    title: str
    content: str
    club_id: int
    book_volume_id: Optional[str] = None

class ThreadUpdateRequest(BaseModel):
    title: str
    content: str


class CommentResponse(ResponseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    content: str
    thread_id: int
    author: Optional[UserSummary] = None
    likes_count: int = 0
    is_liked: bool = False

class CommentCreateRequest(BaseModel):
    content: str

class CommentUpdateRequest(BaseModel):
    content: str
