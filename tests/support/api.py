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

    def login_available(self, payload: dict[str, Any]):
        return self._client.post("/api/auth/login-available", json=payload)

    def telegram(self, payload: dict[str, Any]):
        return self._client.post("/api/auth/telegram", json=payload)

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

    def delete_current_user(
        self,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ):
        # client.delete() не принимает json - используем request().
        return self._client.request(
            "DELETE", "/api/users/current", params=params, json=payload, headers=headers
        )

    def create_bookclub(self, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.post("/api/bookclubs", json=payload, headers=headers)

    def genres(self, headers: dict[str, str] | None = None):
        return self._client.get("/api/genres", headers=headers)

    def create_genre(self, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.post("/api/genres", json=payload, headers=headers)

    def update_genre(self, genre_id: int, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.put(f"/api/genres/{genre_id}", json=payload, headers=headers)

    def delete_genre(self, genre_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/genres/{genre_id}", headers=headers)

    def bookclubs(
        self,
        headers: dict[str, str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ):
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return self._client.get("/api/bookclubs", params=params or None, headers=headers)

    def search_bookclubs(
        self,
        headers: dict[str, str] | None = None,
        query: str | None = None,
        genres: list[str] | None = None,
        relation: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ):
        payload: dict[str, Any] = {}
        if query is not None:
            payload["query"] = query
        if genres is not None:
            payload["genres"] = genres
        if relation is not None:
            payload["relation"] = relation
        if limit is not None:
            payload["limit"] = limit
        if offset is not None:
            payload["offset"] = offset
        return self._client.post("/api/bookclubs/search", json=payload, headers=headers)

    def bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.get(f"/api/bookclubs/{club_id}", headers=headers)

    def bookclub_members(
        self,
        club_id: int,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ):
        return self._client.get(f"/api/bookclubs/{club_id}/members", params=params, headers=headers)

    def delete_bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/bookclubs/{club_id}", headers=headers)

    def join_bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.post(f"/api/bookclubs/{club_id}/join", headers=headers)

    def leave_bookclub(self, club_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/bookclubs/{club_id}/leave", headers=headers)

    def set_bookclub_genres(self, club_id: int, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.put(f"/api/bookclubs/{club_id}/genres", json=payload, headers=headers)

    def update_bookclub(self, club_id: int, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.patch(f"/api/bookclubs/{club_id}", json=payload, headers=headers)

    def search_books(self, q: str, headers: dict[str, str] | None = None):
        return self._client.get("/api/books/search", params={"q": q}, headers=headers)

    def create_book(self, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.post("/api/books", json=payload, headers=headers)

    def create_thread(self, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.post("/api/threads", json=payload, headers=headers)

    def threads(
        self,
        club_id: int,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ):
        return self._client.get(f"/api/threads/{club_id}", params=params, headers=headers)

    def update_thread(self, thread_id: int, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.put(f"/api/threads/{thread_id}", json=payload, headers=headers)

    def delete_thread(self, thread_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/threads/{thread_id}", headers=headers)

    def create_comment(self, thread_id: int, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.post(f"/api/threads/{thread_id}/comments", json=payload, headers=headers)

    def comments(
        self,
        thread_id: int,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ):
        return self._client.get(f"/api/threads/{thread_id}/comments", params=params, headers=headers)

    def update_comment(self, comment_id: int, payload: dict[str, Any], headers: dict[str, str] | None = None):
        return self._client.put(f"/api/comments/{comment_id}", json=payload, headers=headers)

    def delete_comment(self, comment_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/comments/{comment_id}", headers=headers)

    def comment_likers(
        self,
        comment_id: int,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ):
        return self._client.get(f"/api/comments/{comment_id}/likes", params=params, headers=headers)

    def like_comment(self, comment_id: int, headers: dict[str, str] | None = None):
        return self._client.post(f"/api/comments/{comment_id}/like", headers=headers)

    def unlike_comment(self, comment_id: int, headers: dict[str, str] | None = None):
        return self._client.delete(f"/api/comments/{comment_id}/like", headers=headers)
