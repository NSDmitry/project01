from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.deps import get_club_repository
from app.bookclubs.repository import BookClubRepository
from app.core.database import get_db
from app.discussions.repository import ThreadRepository, CommentRepository
from app.discussions.service import ThreadService, CommentService


def get_thread_repository(db: AsyncSession = Depends(get_db)) -> ThreadRepository:
    return ThreadRepository(db)

def get_comment_repository(db: AsyncSession = Depends(get_db)) -> CommentRepository:
    return CommentRepository(db)

def get_thread_service(
    thread_repository: ThreadRepository = Depends(get_thread_repository),
    book_club_repository: BookClubRepository = Depends(get_club_repository),
) -> ThreadService:
    return ThreadService(
        thread_repository=thread_repository,
        book_club_repository=book_club_repository,
    )

def get_comment_service(
    comment_repository: CommentRepository = Depends(get_comment_repository),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
    book_club_repository: BookClubRepository = Depends(get_club_repository),
) -> CommentService:
    return CommentService(
        comment_repository=comment_repository,
        thread_repository=thread_repository,
        book_club_repository=book_club_repository,
    )
