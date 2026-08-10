"""Порты - то, что нужно тредам от соседних доменов.

См. app/bookclubs/ports.py - тот же принцип: сервис зависит от протокола, deps.py
подставляет репозиторий соседа сейчас и HTTP-клиент после распила.
"""
from typing import Any, List, Protocol

from app.core.contracts import UserSummary


class UsersPort(Protocol):
    async def get_summaries_by_ids(self, user_ids: List[int]) -> List[UserSummary]: ...


class ClubsPort(Protocol):
    # get_book_club поднимает NotFound, если клуба нет - тредам важен сам факт
    # существования и club_id/owner_id из результата.
    async def get_book_club(self, club_id: int) -> Any: ...
    async def is_member(self, club_id: int, user_id: int) -> bool: ...


class BooksPort(Protocol):
    # Возвращает книгу с полем id (в монолите - ORM, после распила - DTO книги).
    async def get_or_create_book(self, volume_id: str) -> Any: ...


class ReadingsPort(Protocol):
    # id клуба, которому принадлежит этап захода, либо None - этапа нет. Тредам
    # хватает этого, чтобы проверить, что этап из того же клуба.
    async def get_stage_club_id(self, stage_id: int) -> int | None: ...
