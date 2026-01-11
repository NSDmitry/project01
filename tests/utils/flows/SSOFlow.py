from dataclasses import dataclass
from typing import Dict
from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.mock_factories.AuthMockFactory import AuthMockFactory

@dataclass
class AuthenticatedUser:
    sid: str
    headers: Dict[str, str]
    phone_number: str
    user_id: int

class AuthTestFlow:
    @staticmethod
    def register(client: TestClient, payload=None) -> AuthenticatedUser:
        if payload is None:
            payload = AuthMockFactory.make_register_payload()

        response = APIRouter.SSO.sign_up(client, payload)

        data = response.json()["data"]
        sid = data["session_id"]

        return AuthenticatedUser(
            sid=sid,
            headers={"X-Session-Id": sid},
            phone_number=data.get("phone_number"),
            user_id=data.get("id"),
        )