from app.core.errors.errors import Forbidden
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.db.models import DBUser
from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.comment_repository import CommentRepository
from app.db.repositories.thread_repository import ThreadRepository
from app.schemas.comments_schema import CommentResponseModel, CommentCreateRequestModel, CommentUpdateRequestModel


class CommentService:
    comment_repository: CommentRepository
    thread_repository: ThreadRepository
    book_club_repository: BookClubRepository

    def __init__(
            self,
            comment_repository: CommentRepository,
            thread_repository: ThreadRepository,
            book_club_repository: BookClubRepository,
        ) -> None:

        self.comment_repository = comment_repository
        self.thread_repository = thread_repository
        self.book_club_repository = book_club_repository

    async def get_comments(self, thread_id: int, limit: int, offset: int) -> ResponseModel[Page[CommentResponseModel]]:
        """
        Получение комментариев треда (старые сверху, постранично).
        :param thread_id: Id треда
        :param limit: Размер страницы
        :param offset: Смещение
        :return: Страница комментариев
        """
        thread = await self.thread_repository.get_thread(thread_id)
        comments, total = await self.comment_repository.get_comments(thread.id, limit=limit, offset=offset)

        page = Page(
            items=[CommentResponseModel.model_validate(comment) for comment in comments],
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def create_comment(
        self, user: DBUser, thread_id: int, model: CommentCreateRequestModel
    ) -> ResponseModel[CommentResponseModel]:
        """
        Создание комментария в треде.
        :param user: пользователь
        :param thread_id: Id треда
        :param model: CommentCreateRequestModel
        :return: ResponseModel[CommentResponseModel]
        """
        thread = await self.thread_repository.get_thread(thread_id)

        if not await self.book_club_repository.is_member(thread.club_id, user.id):
            raise Forbidden(errors=["Оставлять комментарии могут только участники клуба"])

        db_comment = await self.comment_repository.create_comment(thread.id, user.id, model)

        return ResponseModel.ok(CommentResponseModel.model_validate(db_comment))

    async def update_comment(
        self, user: DBUser, comment_id: int, model: CommentUpdateRequestModel
    ) -> ResponseModel[CommentResponseModel]:
        """
        Редактирование комментария.
        :param user:
        :param comment_id:
        :param model:
        :return:
        """
        db_comment = await self.comment_repository.get_comment(comment_id)

        if db_comment.author_id != user.id:
            raise Forbidden(errors=["Редактировать комментарий может только автор"])

        db_comment = await self.comment_repository.update_comment(db_comment, model)

        return ResponseModel.ok(CommentResponseModel.model_validate(db_comment))

    async def delete_comment(self, user: DBUser, comment_id: int) -> ResponseModel:
        """
        Удаление комментария.
        :param user:
        :param comment_id:
        :return:
        """
        db_comment = await self.comment_repository.get_comment(comment_id)
        db_thread = await self.thread_repository.get_thread(db_comment.thread_id)
        db_club = await self.book_club_repository.get_book_club(db_thread.club_id)

        if db_comment.author_id != user.id and user.id != db_club.owner_id:
            raise Forbidden(errors=["Удалять комментарий может только автор комментария, или владелец клуба"])

        await self.comment_repository.delete_comment(comment_id)

        return ResponseModel.ok(message="Комментарий успешно удалён")
