"""Порты - то, что нужно клубам от соседних доменов.

Сервис типизируется этими протоколами, а не конкретными репозиториями соседей.
В монолите их реализуют репозитории iam/genres (структурно подходят, адаптер не
нужен), инстанс подставляет deps.py. После распила deps.py заменит репозиторий на
HTTP-клиент - протокол и вызовы сервиса не меняются.

Возвращаемые типы - контракты (core.contracts), а не ORM: клуб получает от соседа
готовый DTO. В монолите под аннотацией ходит ORM-объект (у него те же поля), после
распила - тот же контракт из JSON.
"""
from typing import Any, List, Protocol

from app.core.contracts import GenreResponse, UserSummary


class UsersPort(Protocol):
    async def get_summaries_by_ids(self, user_ids: List[int]) -> List[UserSummary]: ...


class GenresPort(Protocol):
    async def get_by_codes(self, codes: List[str]) -> List[GenreResponse]: ...
    async def get_by_ids(self, ids: List[int]) -> List[GenreResponse]: ...


class BooksPort(Protocol):
    # Возвращает книгу с полем id (в монолите - ORM, после распила - DTO книги).
    async def get_or_create_book(self, volume_id: str) -> Any: ...
