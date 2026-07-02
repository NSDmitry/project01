from app.core.errors.errors import Forbidden
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.thread_repository import ThreadRepository
from app.schemas.threads_schema import ThreadResponseModel, ThreadCreateRequestModel


class ThreadService:
    thread_repository: ThreadRepository
    book_club_repository: BookClubRepository

    def __init__(
            self,
            thread_repository: ThreadRepository,
            book_club_repository: BookClubRepository,
        ) -> None:

        self.thread_repository = thread_repository
        self.book_club_repository = book_club_repository

    async def get_threads(self, book_club_id: int, limit: int, offset: int) -> ResponseModel[Page[ThreadResponseModel]]:
        """
        Получение тредов книжного клуба (последние сверху, постранично).
        :param book_club_id: Id книжного клуба
        :param limit: Размер страницы
        :param offset: Смещение
        :return: Страница тредов
        """
        club = await self.book_club_repository.get_book_club(club_id=book_club_id)
        threads, total = await self.thread_repository.get_threads(club.id, limit=limit, offset=offset)

        page = Page(
            items=[ThreadResponseModel.model_validate(thread) for thread in threads],
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def create_thread(self, user: DBUser, model: ThreadCreateRequestModel) -> ResponseModel[ThreadResponseModel]:
        """
        Создание треда в книжном клубе.
        :param user: токен доступа
        :param model: ThreadCreateRequestModel
        :return: ResponseModel[ThreadResponseModel]
        """
        await self.book_club_repository.get_book_club(model.club_id)

        if not await self.book_club_repository.is_member(model.club_id, user.id):
            raise Forbidden(errors=["Создавать треды могут только участники клуба"])

        db_thread = await self.thread_repository.create_thread(user.id, model)

        return ResponseModel.ok(ThreadResponseModel.model_validate(db_thread))

    async def delete_thread(self, user: DBUser, thread_id: int) -> ResponseModel:
        """
        Удаление треда.
        :param user:
        :param thread_id:
        :return:
        """

        db_thread = await self.thread_repository.get_thread(thread_id)

        if db_thread.author_id != user.id:
            raise Forbidden(errors=["Удалять треды может только автор треда"])

        await self.thread_repository.delete_thread(thread_id)

        return ResponseModel.ok(message="Тред успешно удалён")

    async def update_thread(
        self,
        user: DBUser,
        thread_id: int,
        model: ThreadCreateRequestModel
    ) -> ResponseModel[ThreadResponseModel]:
        """
        Обновление треда.
        :param user:
        :param thread_id:
        :param model:
        :return:
        """
        db_thread = await self.thread_repository.get_thread(thread_id)
        db_club = await self.book_club_repository.get_book_club(db_thread.club_id)

        if db_thread.author_id != user.id and user.id != db_club.owner_id:
            raise Forbidden(errors=["Изменять тред может только автор треда, или владелец клуба"])

        db_thread = await self.thread_repository.update_thread(db_thread, model)

        return ResponseModel.ok(ThreadResponseModel.model_validate(db_thread))
