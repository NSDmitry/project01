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

    class BookClubs:
        @staticmethod
        def get_all_book_clubs(client: TestClient):
            return client.get("/api/bookclubs")

        @staticmethod
        def create_book_club(client: TestClient, payload: Dict, headers: Dict):
            return client.post(f"/api/bookclubs", json=payload, headers=headers)

        @staticmethod
        def delete_book_club(client: TestClient, club_id: int, headers: Dict):
            return client.delete(f"/api/bookclubs/{club_id}", headers=headers)

        @staticmethod
        def get_owned_book_clubs(client: TestClient, headers: Dict):
            return client.get(f"/api/bookclubs/owned", headers=headers)

        @staticmethod
        def get_book_club_by_id(client: TestClient, club_id: int):
            return client.get(f"/api/bookclubs/{club_id}")

        @staticmethod
        def join_book_club(client: TestClient, club_id: int, headers: Dict):
            return client.post(f"/api/bookclubs/{club_id}/join", headers=headers)

        @staticmethod
        def leave_book_club(client: TestClient, club_id: int, headers: Dict):
            return client.delete(f"/api/bookclubs/{club_id}/leave", headers=headers)