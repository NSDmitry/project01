from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import ResponseSchema
from app.schemas.public_user_schema import UserSummary


class ThreadResponse(ResponseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
    title: str
    content: str
    club_id: int
    author: Optional[UserSummary] = None

class ThreadCreateRequest(BaseModel):
    title: str
    content: str
    club_id: int

class ThreadUpdateRequest(BaseModel):
    title: str
    content: str