from __future__ import annotations

from dataclasses import dataclass

from tests.support.api import ApiClient
from tests.support.factories import AuthFactory, BookclubFactory


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
        data = response.json()["data"]
        return AuthSession(
            user_id=data["id"],
            phone_number=data.get("phone_number"),
            session_id=data["session_id"],
        )


class BookclubFlow:
    @staticmethod
    def create(api: ApiClient, auth: AuthSession | None = None, payload: dict | None = None):
        current_auth = auth or AuthFlow.register(api)
        current_payload = payload or BookclubFactory.payload()
        return api.create_bookclub(current_payload, headers=current_auth.headers)
