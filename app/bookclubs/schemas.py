from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime

from app.core.contracts import BookResponse, GenreResponse, UserSummary
from app.core.params import MAX_OFFSET
from app.core.schemas import ResponseSchema

class BookClubRelation(str, Enum):
    owner = "owner"
    member = "member"

class ClubPrivacy(str, Enum):
    """Как попасть в клуб: свободно, по заявке или по коду приглашения."""
    public = "public"
    by_request = "by_request"
    by_invite = "by_invite"

class ClubRole(str, Enum):
    owner = "owner"
    moderator = "moderator"
    member = "member"

class JoinRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class CreateBookClubRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=500)
    genres: list[str] = Field(max_length=5)
    privacy: ClubPrivacy = ClubPrivacy.public

class UpdateBookClubRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, min_length=3, max_length=500)
    privacy: Optional[ClubPrivacy] = None

class CreateInviteRequest(BaseModel):
    # None - код бессрочный.
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)

class JoinByInviteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)

class UpdateMemberRoleRequest(BaseModel):
    # Владение передаётся отдельной операцией - роль владельца здесь не назначается.
    role: Literal[ClubRole.moderator, ClubRole.member]

class TransferOwnershipRequest(BaseModel):
    user_id: int = Field(ge=1)

class UpdateBookClubGenresRequest(BaseModel):
    genres: list[str] = Field(max_length=5)

class SearchBookClubsRequest(BaseModel):
    query: Optional[str] = None
    # Жанры - отдельный фильтр, а не слова в query: они сужают выдачу (AND),
    # а не расширяют её, и не участвуют в ранжировании по тексту.
    genres: list[str] = []
    relation: Optional[BookClubRelation] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0, le=MAX_OFFSET)

class ReadingStageRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date
    # Последняя страница этапа. Без неё прогресс по номеру страницы к этапу
    # не привязывается - только явным выбором этапа.
    end_page: Optional[int] = Field(default=None, ge=1)

class ReadingScheduleRequest(BaseModel):
    """Сроки захода и его этапы - общее у создания захода и закрытия голосования."""
    started_at: date
    deadline: date
    stages: list[ReadingStageRequest] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def check_schedule(self) -> "ReadingScheduleRequest":
        if self.deadline < self.started_at:
            raise ValueError("Дедлайн не может быть раньше даты старта")

        previous_date: date | None = None
        previous_page: int | None = None
        for stage in self.stages:
            if not self.started_at <= stage.due_date <= self.deadline:
                raise ValueError("Дата этапа должна попадать в интервал от старта до дедлайна")
            if previous_date is not None and stage.due_date <= previous_date:
                raise ValueError("Даты этапов должны идти строго по возрастанию")
            if stage.end_page is not None:
                if previous_page is not None and stage.end_page <= previous_page:
                    raise ValueError("Страницы этапов должны идти строго по возрастанию")
                previous_page = stage.end_page
            previous_date = stage.due_date

        return self

class CreateReadingRequest(ReadingScheduleRequest):
    book_volume_id: str = Field(min_length=1, max_length=100)

class CreateNominationRequest(BaseModel):
    book_volume_id: str = Field(min_length=1, max_length=100)

class UpdateReadingProgressRequest(BaseModel):
    # Этап важнее страницы: если пришли оба, страница сохраняется как есть, но
    # в графике участника считает выбранный этап.
    stage_id: Optional[int] = Field(default=None, ge=1)
    page: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_any(self) -> "UpdateReadingProgressRequest":
        if self.stage_id is None and self.page is None:
            raise ValueError("Нужно передать этап или страницу")

        return self

class ReadingStageResponse(ResponseSchema):
    id: int
    position: int
    title: str
    due_date: date
    end_page: Optional[int] = None

class ReadingResponse(ResponseSchema):
    id: int
    club_id: int
    book: Optional[BookResponse] = None
    started_at: date
    deadline: date
    # None - заход идёт прямо сейчас.
    finished_at: Optional[datetime] = None
    stages: list[ReadingStageResponse] = []

class ReadingProgressSummary(ResponseSchema):
    members_count: int = 0
    # Сколько участников закрыли этап, чья дата уже наступила.
    on_track_count: int = 0
    on_track_ratio: float = 0.0
    # Этап, который должен быть закрыт к сегодняшнему дню. None - ни один срок
    # ещё не наступил, тогда в графике считаются все.
    current_stage: Optional[ReadingStageResponse] = None

class CurrentReadingResponse(ResponseSchema):
    reading: ReadingResponse
    progress: ReadingProgressSummary

class CurrentReadingSummary(ResponseSchema):
    """Текущий заход в карточке клуба - без этапов и поимённого прогресса."""
    id: int
    book: Optional[BookResponse] = None
    deadline: date
    on_track_ratio: float = 0.0

class ReadingProgressResponse(ResponseSchema):
    user: Optional[UserSummary] = None
    stage: Optional[ReadingStageResponse] = None
    page: Optional[int] = None
    on_track: bool = False
    updated_at: datetime

class ClubMemberResponse(UserSummary):
    """Участник клуба - сводка пользователя плюс его роль в этом клубе."""
    role: ClubRole = ClubRole.member

class InviteResponse(ResponseSchema):
    club_id: int
    code: str
    # None - код бессрочный.
    expires_at: Optional[datetime] = None

class JoinRequestResponse(ResponseSchema):
    id: int
    club_id: int
    # None - пользователь удалил аккаунт, пока заявка ждала решения.
    user: Optional[UserSummary] = None
    status: JoinRequestStatus
    created_at: datetime

class NominationResponse(ResponseSchema):
    id: int
    club_id: int
    book: Optional[BookResponse] = None
    votes_count: int = 0
    # Голос текущего пользователя отдан за эту номинацию.
    voted: bool = False

class BookClubResponse(ResponseSchema):
    id: int
    name: str
    description: str
    privacy: ClubPrivacy = ClubPrivacy.public
    created_at: datetime
    owner: Optional[UserSummary] = None
    members_count: int = 0
    threads_count: int = 0
    genres: list[GenreResponse] = []
    # None - клуб сейчас ничего не читает.
    current_reading: Optional[CurrentReadingSummary] = None
