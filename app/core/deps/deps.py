from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.book_club_repository import BookClubRepository
from app.db.repositories.discussion_repository import DiscussionRepository

from app.api.services.user_service import UserService
from app.api.services.book_club_service import BookClubSerivce
from app.api.services.discussion_service import DiscussionService
from app.api.services.sso_service import SSOService


######## repositories ########

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_club_repository(db: Session = Depends(get_db)) -> BookClubRepository:
    return BookClubRepository(db)

def get_discussion_repository(db: Session = Depends(get_db)) -> DiscussionRepository:
    return DiscussionRepository(db)


######## services ########

def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repository=user_repository)

def get_book_club_service(
    user_repository: UserRepository = Depends(get_user_repository),
    book_club_repository: BookClubRepository = Depends(get_club_repository),
) -> BookClubSerivce:
    return BookClubSerivce(
        user_repository=user_repository,
        book_club_repository=book_club_repository,
    )

def get_discussion_service(
    discussion_repository: DiscussionRepository = Depends(get_discussion_repository),
    book_club_repository: BookClubRepository = Depends(get_club_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> DiscussionService:
    return DiscussionService(
        discussion_repository=discussion_repository,
        book_club_repository=book_club_repository,
        user_repository=user_repository,
    )

def get_sso_service(
    user_service: UserService = Depends(get_user_service),
    user_repository: UserRepository = Depends(get_user_repository),
) -> SSOService:
    return SSOService(
        user_service=user_service,
        user_repository=user_repository,
    )