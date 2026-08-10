from typing import List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts import GenreResponse
from app.genres.models import Genre
from app.core.errors.errors import Conflict, NotFound


class GenreRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self) -> List[Genre]:
        result = await self.db.execute(
            select(Genre).order_by(Genre.sort_order)
        )

        return list(result.scalars().all())

    # get_by_codes/get_by_ids - адаптер порта GenresPort для соседних доменов,
    # поэтому отдают контракт из core, а не ORM-модель жанра.
    async def get_by_codes(self, codes: List[str]) -> List[GenreResponse]:
        result = await self.db.execute(
            select(Genre).where(Genre.code.in_(codes))
        )

        return [GenreResponse.model_validate(genre) for genre in result.scalars().all()]

    async def get_by_ids(self, ids: List[int]) -> List[GenreResponse]:
        if not ids:
            return []

        # id вторым ключом - детерминированный порядок при равных sort_order
        result = await self.db.execute(
            select(Genre).where(Genre.id.in_(ids)).order_by(Genre.sort_order, Genre.id)
        )

        return [GenreResponse.model_validate(genre) for genre in result.scalars().all()]

    async def get_by_id(self, genre_id: int) -> Genre:
        genre = await self.db.get(Genre, genre_id)

        if genre is None:
            raise NotFound("Жанр с таким id не найден")

        return genre

    async def create(self, code: str, name: str, sort_order: int) -> Genre:
        genre = Genre(code=code, name=name, sort_order=sort_order)
        self.db.add(genre)

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(message="Жанр с таким кодом уже существует")

        return genre

    async def update(self, genre_id: int, code: str, name: str, sort_order: int) -> Genre:
        genre = await self.get_by_id(genre_id)
        genre.code = code
        genre.name = name
        genre.sort_order = sort_order

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflict(message="Жанр с таким кодом уже существует")

        return genre

    async def delete(self, genre_id: int) -> None:
        genre = await self.get_by_id(genre_id)

        await self.db.delete(genre)
        await self.db.flush()
