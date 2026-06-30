from typing import List

from app.core.errors.errors import Conflict
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.discussion_repository import DiscussionRepository
from app.db.repositories.user_repository import UserRepository
from app.schemas.discussions_schema import DisscussionResponseModel, DiscussionCreateRequestModel


class DiscussionService:
    discussion_repository: DiscussionRepository
    book_club_repository: BookClubRepository
    user_repository: UserRepository

    def __init__(
            self,
            discussion_repository: DiscussionRepository,
            book_club_repository: BookClubRepository,
            user_repository: UserRepository
        ) -> None:

        self.discussion_repository = discussion_repository
        self.book_club_repository = book_club_repository
        self.user_repository = user_repository

    async def get_disscussions(self, book_club_id: int) -> ResponseModel[List[DisscussionResponseModel]]:
        """
        Получение всех обсуждений книжного клуба.
        :param book_club_id: Id книжного клуба
        :return: Список обсуждений
        """
        club = await self.book_club_repository.get_book_club(club_id=book_club_id)
        discussions = await self.discussion_repository.get_discussions(book_club_id=club.id)

        return ResponseModel.ok([DisscussionResponseModel.model_validate(discussion) for discussion in discussions])

    async def create_discussion(self, user: DBUser, model: DiscussionCreateRequestModel) -> ResponseModel[DisscussionResponseModel]:
        """
        Создание обсуждения в книжном клубе.
        :param user: токен доступа
        :param model: DiscussionCreateRequestModel
        :return: ResponseModel[DisscussionResponseModel]
        """
        user = await self.user_repository.get_user_by_id(user.id)
        db_book_club = await self.book_club_repository.get_book_club(model.club_id)

        if user.id not in db_book_club.members_ids:
            raise Conflict(errors=["Создавать обсуждения могут только участники клуба"])

        db_disscussion = await self.discussion_repository.create_discussion(user.id, model)

        return ResponseModel.ok(DisscussionResponseModel.model_validate(db_disscussion))

    async def delete_discussion(self, user: DBUser, discussion_id: int) -> ResponseModel:
        """
        Удаление обсуждения.
        :param user:
        :param discussion_id:
        :return:
        """

        db_disscussion = await self.discussion_repository.get_discussion(discussion_id)

        if db_disscussion.author_id != user.id:
            raise Conflict(errors=["Удалять обсуждения может только автор обсуждения"])

        await self.discussion_repository.delete_discussion(discussion_id)

        return ResponseModel.ok(message="Обсуждение успешно удалено")

    async def update_discussion(
        self,
        user: DBUser,
        discussion_id: int,
        model: DiscussionCreateRequestModel
    ) -> ResponseModel[DisscussionResponseModel]:
        """
        Обновление обсуждения.
        :param user:
        :param discussion_id:
        :param model:
        :return:
        """
        db_disscussion = await self.discussion_repository.get_discussion(discussion_id)
        db_club = await self.book_club_repository.get_book_club(db_disscussion.club_id)

        if db_disscussion.author_id != user.id or user.id != db_club.owner_id:
            raise Conflict(errors=["Изменять обсуждение может только автор обсуждения, или владелец клуба"])

        db_disscussion = await self.discussion_repository.update_discussion(db_disscussion, model)

        return ResponseModel.ok(DisscussionResponseModel.model_validate(db_disscussion))
