from typing import List

from app.genres.models import Genre
from app.core import events
from app.core.authorization import require_permission
from app.core.models.response_model import ResponseModel
from app.genres.repository import GenreRepository
from app.core.contracts import Principal
from app.genres.schemas import CreateGenreRequest, UpdateGenreRequest, GenreResponse


class GenreService:
    genre_repository: GenreRepository

    def __init__(self, genre_repository: GenreRepository) -> None:
        self.genre_repository = genre_repository

    async def list_genres(self) -> ResponseModel[List[GenreResponse]]:
        genres: List[Genre] = await self.genre_repository.list_all()

        return ResponseModel.ok([GenreResponse.model_validate(genre) for genre in genres])

    async def create_genre(self, user: Principal, model: CreateGenreRequest) -> ResponseModel[GenreResponse]:
        require_permission(user, message="Управлять жанрами может только администратор")

        genre: Genre = await self.genre_repository.create(model.code, model.name, model.sort_order)

        return ResponseModel.ok(GenreResponse.model_validate(genre))

    async def update_genre(
        self, user: Principal, genre_id: int, model: UpdateGenreRequest
    ) -> ResponseModel[GenreResponse]:
        require_permission(user, message="Управлять жанрами может только администратор")

        genre: Genre = await self.genre_repository.update(genre_id, model.code, model.name, model.sort_order)

        return ResponseModel.ok(GenreResponse.model_validate(genre))

    async def delete_genre(self, user: Principal, genre_id: int) -> ResponseModel:
        require_permission(user, message="Управлять жанрами может только администратор")

        await self.genre_repository.delete(genre_id)
        await events.publish(events.GENRES_DELETED, {"genre_ids": [genre_id]})

        return ResponseModel.ok(message="Жанр успешно удален")
