from typing import List

from app.core.errors.errors import Conflict
from app.core.models.response_model import ResponseModel
from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.discussion_repository import DiscussionRepository
from app.db.repositories.user_repository import UserRepository
from app.schemas.discussions_schema import DisscussionResponseModel, DiscussionCreateRequestModel


class DiscussionService:
    discussion_repository: DiscussionRepository
    book_club_repository: BookClubRepository
    user_repository: UserRepository

    def __init__(self) -> None:
        self.discussion_repository = DiscussionRepository()
        self.book_club_repository = BookClubRepository()
        self.user_repository = UserRepository()

    def get_disscussions(self, book_club_id: int) -> ResponseModel[List[DisscussionResponseModel]]:
        """
        Получение всех обсуждений книжного клуба.
        :param book_club_id: id книжного клуба
        :return: Список обсуждений
        """
        club = self.book_club_repository.get_book_club(club_id=book_club_id)
        discussions = self.discussion_repository.get_discussions(book_club_id=club.id)

        return ResponseModel.success_response([DisscussionResponseModel(**discussion.to_dict()) for discussion in discussions])

    def create_discussion(self, access_token: str, model: DiscussionCreateRequestModel) -> ResponseModel[DisscussionResponseModel]:
        """
        Создание обсуждения в книжном клубе.
        :param access_token: токен доступа
        :param model: DiscussionCreateRequestModel
        :return: ResponseModel[DisscussionResponseModel]
        """
        db_user = self.user_repository.get_user_by_access_token(access_token)
        db_book_club = self.book_club_repository.get_book_club(model.club_id)

        if db_user.id not in db_book_club.members_ids:
            raise Conflict(errors=["Создавать обсуждения могут только участники клуба"])

        db_disscussion = self.discussion_repository.create_discussion(db_user.id, model)

        return ResponseModel.success_response(DisscussionResponseModel(**db_disscussion.to_dict()))

    def delete_discussion(self, access_token: str, discussion_id: int) -> ResponseModel:
        """
        Удаление обсуждения.
        :param access_token:
        :param discussion_id:
        :return:
        """

        db_user = self.user_repository.get_user_by_access_token(access_token)
        db_disscussion = self.discussion_repository.get_discussion(discussion_id)

        if db_disscussion.author_id != db_user.id:
            raise Conflict(errors=["Удалять обсуждения может только автор обсуждения"])

        self.discussion_repository.delete_discussion(discussion_id)

        return ResponseModel.success_response(message="Обсуждение успешно удалено")

    def update_discussion(
        self,
        access_token: str,
        discussion_id: int,
        model: DiscussionCreateRequestModel
    ) -> ResponseModel[DisscussionResponseModel]:
        """
        Обновление обсуждения.
        :param access_token:
        :param discussion_id:
        :param model:
        :return:
        """
        db_user = self.user_repository.get_user_by_access_token(access_token)
        db_disscussion = self.discussion_repository.get_discussion(discussion_id)
        db_club = self.book_club_repository.get_book_club(db_disscussion.club_id)

        if db_disscussion.author_id != db_user.id or db_user.id != db_club.owner_id:
            raise Conflict(errors=["Изменять обсуждение может только автор обсуждения, или владелец клуба"])

        db_disscussion = self.discussion_repository.update_discussion(db_disscussion, model)

        return ResponseModel.success_response(DisscussionResponseModel(**db_disscussion.to_dict()))
