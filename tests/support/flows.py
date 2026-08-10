from __future__ import annotations

from dataclasses import dataclass

from tests.support.api import ApiClient
from tests.support.factories import AuthFactory, BookclubFactory, ReadingFactory
from tests.support.google_books import install_fake_google, suggestion


@dataclass(frozen=True)
class AuthSession:
    user_id: int
    phone_number: int | str | None
    session_id: str

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Session-Id": self.session_id}


class AuthFlow:
    @staticmethod
    def register(api: ApiClient, payload: dict | None = None) -> AuthSession:
        response = api.register(payload or AuthFactory.register_payload())
        session_id = response.json()["data"]["session_id"]

        # register отдаёт только session_id - за остальными данными пользователя
        # идём отдельным запросом, как это делает реальный клиент.
        current = api.current_user(headers={"X-Session-Id": session_id}).json()["data"]

        return AuthSession(
            user_id=current["id"],
            phone_number=current.get("phone_number"),
            session_id=session_id,
        )


class BookclubFlow:
    @staticmethod
    def create(api: ApiClient, auth: AuthSession | None = None, payload: dict | None = None):
        current_auth = auth or AuthFlow.register(api)
        current_payload = payload or BookclubFactory.payload()
        return api.create_bookclub(current_payload, headers=current_auth.headers)


class ReadingFlow:
    @staticmethod
    def create(
        api: ApiClient,
        club_id: int,
        owner: AuthSession,
        payload: dict | None = None,
        volume_id: str = "vol-1",
    ):
        # Книга приезжает из Google Books - в тестах клиент подменён.
        install_fake_google([suggestion(volume_id=volume_id)])
        return api.create_reading(
            club_id,
            payload or ReadingFactory.payload(book_volume_id=volume_id),
            headers=owner.headers,
        )


class MemberFlow:
    @staticmethod
    def join(api: ApiClient, club_id: int) -> AuthSession:
        member = AuthFlow.register(api)
        api.join_bookclub(club_id, headers=member.headers)

        return member

    @staticmethod
    def join_by_invite(api: ApiClient, club_id: int, owner: AuthSession) -> AuthSession:
        """Вступление по приглашению - работает при любом режиме приватности клуба."""
        code = api.create_invite(club_id, headers=owner.headers).json()["data"]["code"]
        member = AuthFlow.register(api)
        api.join_by_invite(code, headers=member.headers)

        return member

    @staticmethod
    def moderator(api: ApiClient, club_id: int, owner: AuthSession) -> AuthSession:
        member = MemberFlow.join_by_invite(api, club_id, owner)
        api.set_member_role(club_id, member.user_id, "moderator", headers=owner.headers)

        return member
