from typing import Dict

from starlette.testclient import TestClient

class APIRouter:
    class SSO:
        @staticmethod
        def sign_up(client: TestClient, payload: Dict):
            return client.post("/api/SSO/signup", json=payload)

        @staticmethod
        def sign_in(client: TestClient, payload: Dict):
            return client.post("/api/SSO/signin", json=payload)

    class Users:
        @staticmethod
        def current_user(client: TestClient, headers: Dict = None):
            return client.get("/api/users/current", headers=headers)

        @staticmethod
        def public_user_info(client: TestClient, user_id: int):
            return client.get(f"/api/users/public?user_id={user_id}")

        @staticmethod
        def change_current_user_info(client: TestClient, payload: Dict, headers: Dict):
            return client.put("/api/users", json=payload, headers=headers)