from typing import Optional, Sequence

from app.core import events
from app.core.authorization import require_permission
from app.core.contracts import Principal, UserSummary
from app.core.errors.errors import Forbidden
from app.core.models.page_model import Page
from app.core.models.response_model import ResponseModel
from app.threads.models import Comment, Thread
from app.threads.ports import BooksPort, ClubsPort, UsersPort
from app.threads.repository import ThreadRepository, CommentRepository
from app.threads.schemas import (
    ThreadResponse,
    ThreadCreateRequest,
    ThreadUpdateRequest,
    CommentResponse,
    CommentCreateRequest,
    CommentUpdateRequest,
)


class ThreadService:
    thread_repository: ThreadRepository
    book_club_repository: ClubsPort
    book_service: BooksPort
    user_repository: UsersPort

    def __init__(
            self,
            thread_repository: ThreadRepository,
            book_club_repository: ClubsPort,
            book_service: BooksPort,
            user_repository: UsersPort,
    ) -> None:

        self.thread_repository = thread_repository
        self.book_club_repository = book_club_repository
        self.book_service = book_service
        self.user_repository = user_repository

    # author больше не relationship в модели - тред хранит только author_id.
    # UserSummary подтягиваем батчем из iam (после распила - вызов user-сервиса).
    async def _to_responses(self, threads: Sequence[Thread]) -> list[ThreadResponse]:
        author_ids = {thread.author_id for thread in threads if thread.author_id is not None}
        authors = {}
        if author_ids:
            summaries = await self.user_repository.get_summaries_by_ids(list(author_ids))
            authors = {summary.id: summary for summary in summaries}

        responses = []
        for thread in threads:
            response = ThreadResponse.model_validate(thread)
            response.author = authors.get(thread.author_id) if thread.author_id is not None else None
            responses.append(response)

        return responses

    async def _to_response(self, thread: Thread) -> ThreadResponse:
        return (await self._to_responses([thread]))[0]

    async def get_threads(self, book_club_id: int, limit: int, offset: int) -> ResponseModel[Page[ThreadResponse]]:
        """
        Получение тредов книжного клуба (последние сверху, постранично).
        :param book_club_id: Id книжного клуба
        :param limit: Размер страницы
        :param offset: Смещение
        :return: Страница тредов
        """
        club = await self.book_club_repository.get_book_club(club_id=book_club_id)
        threads = await self.thread_repository.get_threads(club.id, limit=limit, offset=offset)

        page = Page(
            items=await self._to_responses(threads),
            total=club.threads_count,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def create_thread(self, user: Principal, model: ThreadCreateRequest) -> ResponseModel[ThreadResponse]:
        """
        Создание треда в книжном клубе.
        :param user: токен доступа
        :param model: ThreadCreateRequest
        :return: ResponseModel[ThreadResponse]
        """
        await self.book_club_repository.get_book_club(model.club_id)

        if not await self.book_club_repository.is_member(model.club_id, user.id):
            raise Forbidden(errors=["Создавать треды могут только участники клуба"])

        book_id = None
        if model.book_volume_id:
            book = await self.book_service.get_or_create_book(model.book_volume_id)
            book_id = book.id

        db_thread = await self.thread_repository.create_thread(user.id, model, book_id=book_id)
        # Счётчик тредов клуба ведёт домен клубов - уведомляем событием.
        await events.publish(events.THREAD_CREATED, {"club_id": model.club_id})

        return ResponseModel.ok(await self._to_response(db_thread))

    async def delete_thread(self, user: Principal, thread_id: int) -> ResponseModel:
        """
        Удаление треда.
        :param user:
        :param thread_id:
        :return:
        """

        db_thread = await self.thread_repository.get_thread(thread_id)

        require_permission(user, db_thread.author_id, message="Удалять треды может только автор треда")

        await self.thread_repository.delete_thread(thread_id)
        await events.publish(events.THREAD_DELETED, {"club_id": db_thread.club_id, "count": 1})

        return ResponseModel.ok(message="Тред успешно удалён")

    async def update_thread(
            self,
            user: Principal,
            thread_id: int,
            model: ThreadUpdateRequest
    ) -> ResponseModel[ThreadResponse]:
        """
        Обновление треда.
        :param user:
        :param thread_id:
        :param model:
        :return:
        """
        db_thread = await self.thread_repository.get_thread(thread_id)
        db_club = await self.book_club_repository.get_book_club(db_thread.club_id)

        require_permission(
            user, db_thread.author_id, db_club.owner_id,
            message="Изменять тред может только автор треда, или владелец клуба",
        )

        db_thread = await self.thread_repository.update_thread(db_thread, model)

        return ResponseModel.ok(await self._to_response(db_thread))


class CommentService:
    comment_repository: CommentRepository
    thread_repository: ThreadRepository
    book_club_repository: ClubsPort
    user_repository: UsersPort

    def __init__(
            self,
            comment_repository: CommentRepository,
            thread_repository: ThreadRepository,
            book_club_repository: ClubsPort,
            user_repository: UsersPort,
    ) -> None:

        self.comment_repository = comment_repository
        self.thread_repository = thread_repository
        self.book_club_repository = book_club_repository
        self.user_repository = user_repository

    # author больше не relationship - см. комментарий в ThreadService._to_responses.
    async def _authors_by_id(self, comments: Sequence[Comment]) -> dict[int, UserSummary]:
        author_ids = {comment.author_id for comment in comments if comment.author_id is not None}
        if not author_ids:
            return {}

        summaries = await self.user_repository.get_summaries_by_ids(list(author_ids))

        return {summary.id: summary for summary in summaries}

    async def _author_of(self, comment: Comment) -> UserSummary | None:
        if comment.author_id is None:
            return None

        return (await self._authors_by_id([comment])).get(comment.author_id)

    # Единая точка сборки ответа: автор, счётчик и флаг лайка всегда задаются явно.
    @staticmethod
    def _build_response(
        comment: Comment,
        author: UserSummary | None,
        likes_count: int = 0,
        is_liked: bool = False,
    ) -> CommentResponse:
        return CommentResponse.model_validate(comment).model_copy(update={
            "author": author,
            "likes_count": likes_count,
            "is_liked": is_liked,
        })

    async def _to_response(self, comment: Comment) -> CommentResponse:
        return self._build_response(comment, await self._author_of(comment))

    async def get_comments(
            self, thread_id: int, limit: int, offset: int, user: Optional[Principal] = None
    ) -> ResponseModel[Page[CommentResponse]]:
        """
        Получение комментариев треда (старые сверху, постранично).
        :param thread_id: Id треда
        :param limit: Размер страницы
        :param offset: Смещение
        :param user: текущий пользователь (если авторизован) - для расчёта is_liked
        :return: Страница комментариев
        """
        thread = await self.thread_repository.get_thread(thread_id)
        comments = await self.comment_repository.get_comments(thread.id, limit=limit, offset=offset)

        comment_ids = [comment.id for comment in comments]
        likes_counts = await self.comment_repository.get_likes_counts(comment_ids)
        liked_ids = (
            await self.comment_repository.get_liked_comment_ids(comment_ids, user.id)
            if user else set()
        )
        authors = await self._authors_by_id(comments)

        page = Page(
            items=[
                self._build_response(
                    comment,
                    authors.get(comment.author_id) if comment.author_id is not None else None,
                    likes_counts.get(comment.id, 0),
                    comment.id in liked_ids,
                )
                for comment in comments
            ],
            total=thread.comments_count,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def get_comment_likers(self, comment_id: int, limit: int, offset: int) -> ResponseModel[Page[UserSummary]]:
        """
        Получение лайкнувших комментарий (свежие лайки сверху, постранично).
        :param comment_id: Id комментария
        :param limit: Размер страницы
        :param offset: Смещение
        :return: Страница пользователей
        """
        await self.comment_repository.get_comment(comment_id)
        user_ids, total = await self.comment_repository.get_likers(comment_id, limit=limit, offset=offset)

        summaries = await self.user_repository.get_summaries_by_ids(user_ids)
        by_id = {summary.id: summary for summary in summaries}

        page = Page(
            items=[by_id[user_id] for user_id in user_ids if user_id in by_id],
            total=total,
            limit=limit,
            offset=offset,
        )

        return ResponseModel.ok(page)

    async def create_comment(
            self, user: Principal, thread_id: int, model: CommentCreateRequest
    ) -> ResponseModel[CommentResponse]:
        """
        Создание комментария в треде.
        :param user: пользователь
        :param thread_id: Id треда
        :param model: CommentCreateRequest
        :return: ResponseModel[CommentResponse]
        """
        thread = await self.thread_repository.get_thread(thread_id)

        if not await self.book_club_repository.is_member(thread.club_id, user.id):
            raise Forbidden(errors=["Оставлять комментарии могут только участники клуба"])

        db_comment = await self.comment_repository.create_comment(thread.id, user.id, model)

        return ResponseModel.ok(await self._to_response(db_comment))

    async def update_comment(
            self, user: Principal, comment_id: int, model: CommentUpdateRequest
    ) -> ResponseModel[CommentResponse]:
        """
        Редактирование комментария.
        :param user:
        :param comment_id:
        :param model:
        :return:
        """
        db_comment = await self.comment_repository.get_comment(comment_id)

        require_permission(user, db_comment.author_id, message="Редактировать комментарий может только автор")

        db_comment = await self.comment_repository.update_comment(db_comment, model)

        return ResponseModel.ok(await self._to_response(db_comment))

    async def delete_comment(self, user: Principal, comment_id: int) -> ResponseModel:
        """
        Удаление комментария.
        :param user:
        :param comment_id:
        :return:
        """
        db_comment = await self.comment_repository.get_comment(comment_id)
        db_thread = await self.thread_repository.get_thread(db_comment.thread_id)
        db_club = await self.book_club_repository.get_book_club(db_thread.club_id)

        require_permission(
            user, db_comment.author_id, db_club.owner_id,
            message="Удалять комментарий может только автор комментария, или владелец клуба",
        )

        await self.comment_repository.delete_comment(comment_id)

        return ResponseModel.ok(message="Комментарий успешно удалён")

    async def like_comment(self, user: Principal, comment_id: int) -> ResponseModel[CommentResponse]:
        """
        Лайк комментария (идемпотентно - повторный лайк не ошибка).
        :param user: пользователь
        :param comment_id: Id комментария
        :return: ResponseModel[CommentResponse]
        """
        db_comment = await self.comment_repository.get_comment(comment_id)
        db_thread = await self.thread_repository.get_thread(db_comment.thread_id)

        if not await self.book_club_repository.is_member(db_thread.club_id, user.id):
            raise Forbidden(errors=["Ставить лайки могут только участники клуба"])

        await self.comment_repository.add_like(comment_id, user.id)

        return ResponseModel.ok(await self._comment_with_likes(db_comment, is_liked=True))

    async def unlike_comment(self, user: Principal, comment_id: int) -> ResponseModel[CommentResponse]:
        """
        Снятие лайка с комментария (идемпотентно - снятие отсутствующего лайка не ошибка).
        :param user: пользователь
        :param comment_id: Id комментария
        :return: ResponseModel[CommentResponse]
        """
        db_comment = await self.comment_repository.get_comment(comment_id)

        await self.comment_repository.remove_like(comment_id, user.id)

        return ResponseModel.ok(await self._comment_with_likes(db_comment, is_liked=False))

    async def _comment_with_likes(self, comment: Comment, is_liked: bool) -> CommentResponse:
        likes_counts = await self.comment_repository.get_likes_counts([comment.id])

        return self._build_response(
            comment, await self._author_of(comment), likes_counts.get(comment.id, 0), is_liked
        )
