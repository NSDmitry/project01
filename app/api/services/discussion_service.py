from app.core.errors.errors import Conflict
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.discussion_repository import DiscussionRepository
from app.schemas.discussions_schema import DiscussionResponseModel, DiscussionCreateRequestModel


class DiscussionService:
    discussion_repository: DiscussionRepository
    book_club_repository: BookClubRepository

    def __init__(
            self,
            discussion_repository: DiscussionRepository,
            book_club_repository: BookClubRepository,
        ) -> None:

        self.discussion_repository = discussion_repository
        self.book_club_repository = book_club_repository

    async def get_discussions(self, book_club_id: int, limit: int, offset: int) -> ResponseModel[Page[DiscussionResponseModel]]:
        """
        Получение обсуждений книжного клуба (последние сверху, постранично).
        :param book_club_id: Id книжного клуба
        :param limit: Размер страницы
        :param offset: Смещение
        :return: Страница обсуждений
        """
        club = await self.book_club_repository.get_book_club(club_id=book_club_id)
        discussions, total = await self.discussion_repository.get_discussions(club.id, limit=limit, offset=offset)

        page = Page(
            items=[DiscussionResponseModel.model_validate(discussion) for discussion in discussions],
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def create_discussion(self, user: DBUser, model: DiscussionCreateRequestModel) -> ResponseModel[DiscussionResponseModel]:
        """
        Создание обсуждения в книжном клубе.
        :param user: токен доступа
        :param model: DiscussionCreateRequestModel
        :return: ResponseModel[DiscussionResponseModel]
        """
        await self.book_club_repository.get_book_club(model.club_id)

        if not await self.book_club_repository.is_member(model.club_id, user.id):
            raise Conflict(errors=["Создавать обсуждения могут только участники клуба"])

        db_discussion = await self.discussion_repository.create_discussion(user.id, model)

        return ResponseModel.ok(DiscussionResponseModel.model_validate(db_discussion))

    async def delete_discussion(self, user: DBUser, discussion_id: int) -> ResponseModel:
        """
        Удаление обсуждения.
        :param user:
        :param discussion_id:
        :return:
        """

        db_discussion = await self.discussion_repository.get_discussion(discussion_id)

        if db_discussion.author_id != user.id:
            raise Conflict(errors=["Удалять обсуждения может только автор обсуждения"])

        await self.discussion_repository.delete_discussion(discussion_id)

        return ResponseModel.ok(message="Обсуждение успешно удалено")

    async def update_discussion(
        self,
        user: DBUser,
        discussion_id: int,
        model: DiscussionCreateRequestModel
    ) -> ResponseModel[DiscussionResponseModel]:
        """
        Обновление обсуждения.
        :param user:
        :param discussion_id:
        :param model:
        :return:
        """
        db_discussion = await self.discussion_repository.get_discussion(discussion_id)
        db_club = await self.book_club_repository.get_book_club(db_discussion.club_id)

        if db_discussion.author_id != user.id and user.id != db_club.owner_id:
            raise Conflict(errors=["Изменять обсуждение может только автор обсуждения, или владелец клуба"])

        db_discussion = await self.discussion_repository.update_discussion(db_discussion, model)

        return ResponseModel.ok(DiscussionResponseModel.model_validate(db_discussion))
