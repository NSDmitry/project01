from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.contracts import BookResponse, UserSummary
from app.core.schemas import ResponseSchema

TITLE_EMPTY_ERROR = "Заголовок не может быть пустым"
CONTENT_EMPTY_ERROR = "Текст не может быть пустым"


def strip_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise ValueError(TITLE_EMPTY_ERROR)
    return title


def strip_content(content: str) -> str:
    content = content.strip()
    if not content:
        raise ValueError(CONTENT_EMPTY_ERROR)
    return content


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
    title: str = Field(max_length=200)
    content: str = Field(max_length=10000)
    club_id: int
    book_volume_id: Optional[str] = None

    _validate_title = field_validator("title")(strip_title)
    _validate_content = field_validator("content")(strip_content)

class ThreadUpdateRequest(BaseModel):
    title: str = Field(max_length=200)
    content: str = Field(max_length=10000)

    _validate_title = field_validator("title")(strip_title)
    _validate_content = field_validator("content")(strip_content)


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
    content: str = Field(max_length=5000)

    _validate_content = field_validator("content")(strip_content)

class CommentUpdateRequest(BaseModel):
    content: str = Field(max_length=5000)

    _validate_content = field_validator("content")(strip_content)
