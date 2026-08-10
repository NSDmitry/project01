"""Кросс-доменные контракты.

Схемы, которые один домен отдаёт наружу, а другие встраивают в свои ответы
(UserSummary в тредах/клубах, GenreResponse/BookResponse и т.д.). Живут в core,
потому что после распила это wire-контракт между сервисами: у издателя и всех
потребителей форма должна быть одна. Домен-владелец ре-экспортирует свой контракт
из своего schemas.py для внутреннего использования.

Principal - минимальная личность аутентифицированного пользователя. Заменяет
ORM-модель iam.User в сигнатурах чужих доменов: им нужны только id и is_admin,
а не вся модель. В монолите его роль играет iam.User (структурно подходит),
после распила - объект, собранный из доверенных заголовков шлюза.
"""
from typing import Protocol

from app.core.schemas import ResponseSchema


class Principal(Protocol):
    id: int
    is_admin: bool


class UserSummary(ResponseSchema):
    id: int
    name: str


class GenreResponse(ResponseSchema):
    id: int
    code: str
    name: str


class BookResponse(ResponseSchema):
    id: int
    # None - книга создана пользователем вручную, без Google Books.
    google_volume_id: str | None = None
    title: str
    author: str | None = None
    description: str | None = None
    genres: str | None = None
    published_year: int | None = None
    # None - книга заведена вручную или Google не отдал данные.
    cover_url: str | None = None
    page_count: int | None = None
