from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


class ApiClient:
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def register(self, payload: dict[str, Any]):
        return self._client.post("/api/auth/register", json=payload)

    def login(self, payload: dict[str, Any]):
        return self._client.post("/api/auth/login", json=payload)

    def logout(self, headers: dict[str, str] | None = None):
        return self._client.post("/api/auth/logout", headers=headers)

    def current_user(self, headers: dict[str, str] | None = None):
        return self._client.get("/api/users/current", headers=headers)

    def public_user(self, user_id: int, headers: dict[str, str] | None = None):
        return self._client.get(f"/api/users/public?user_id={user_id}", headers=headers)

    def update_user(self, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.put("/api/users", json=payload, headers=headers)

    def change_password(self, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.put("/api/users/password", json=payload, headers=headers)

    def create_bookclub(self, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.post("/api/bookclubs", json=payload, headers=headers)

    def bookclubs(self, headers: dict[str, str] | None = None):
        return self._client.get("/api/bookclubs", headers=headers)

    def owned_bookclubs(self, headers: dict[str, str] | None = None):
        return self._client.get("/api/bookclubs/owned", headers=headers)

    def bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.get(f"/api/bookclubs/{club_id}", headers=headers)

    def delete_bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/bookclubs/{club_id}", headers=headers)

    def join_bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.post(f"/api/bookclubs/{club_id}/join", headers=headers)

    def leave_bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/bookclubs/{club_id}/leave", headers=headers)
