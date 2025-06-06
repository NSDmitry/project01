from fastapi.testclient import TestClient
from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import AuthenticatedUser, SSOTestFlow
from tests.utils.flows.BookclubFlow import BookclubFlow

class TestAllClubs:
    def test_get_all_clubs_unauthorized(self, client: TestClient):
        # Тест на получение всех клубов без авторизации
        response = APIRouter.BookClubs.get_all_book_clubs(client)

        assert response.status_code == 401, \
            f"Ответ должен приходить только с авторизацией: {response.json()}"

    def test_get_all_clubs_empty(self, client: TestClient):
        # Тест на получение всех клубов, когда нет ни одного клуба
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = APIRouter.BookClubs.get_all_book_clubs(client, headers=auth_data.headers)

        assert response.status_code == 200, \
            f"Ошибка при получении списка клубов: {response.json()}"
        assert len(response.json()["data"]) == 0, \
            f"Список клубов должен быть пустым, но получено: {response.json()}"

    def test_get_all_clubs(self, client: TestClient):
        # Тест на получение всех клубов
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        BookclubFlow.create_bookclub(client, auth_data=auth_data)
        response = APIRouter.BookClubs.get_all_book_clubs(client, headers=auth_data.headers)

        assert response.status_code == 200, \
            f"Ошибка при получении списка клубов: {response.json()}"
        assert len(response.json()["data"]) > 0, \
            f"Список клубов не должен быть пустым"

    def test_get_owned_bookclubs(self, client: TestClient):
        # Тест на получение клубов, которыми владеет пользователь
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        BookclubFlow.create_bookclub(client, auth_data=auth_data)

        response = APIRouter.BookClubs.get_owned_book_clubs(client, headers=auth_data.headers)

        assert response.status_code == 200, \
            f"Ошибка при получении списка клубов: {response.json()}"
        assert all(club["owner_id"] == auth_data.user_id for club in response.json()["data"]), \
            f"Все клубы должны принадлежать авторизованному пользователю"

    def test_get_bookclub_by_id(self, client: TestClient):
        # Тест на получение клуба по ID
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_response = BookclubFlow.create_bookclub(client)

        club_id = create_response.json()["data"]["id"]
        response = APIRouter.BookClubs.get_book_club_by_id(client, club_id, headers=auth_data.headers)

        assert response.status_code == 200, \
            f"Ошибка при получении клуба по ID: {response.json()}"
        assert response.json()["data"]["id"] == club_id, \
            "ID клуба не совпадает с ожидаемым: {response.json()}"

    def test_get_bookclub_by_id_unauthorized(self, client: TestClient):
        # Тест на получение клуба по ID без авторизации
        create_response = BookclubFlow.create_bookclub(client)
        club_id = create_response.json()["data"]["id"]
        response = APIRouter.BookClubs.get_book_club_by_id(client, club_id)

        assert response.status_code == 401, \
            f"Ответ должен приходить только с авторизацией: {response.json()}"

    def test_get_bookclub_by_id_not_found(self, client: TestClient):
        # Тест на получение клуба по несуществующему ID
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = APIRouter.BookClubs.get_book_club_by_id(client, club_id=999999, headers=auth_data.headers)

        assert response.status_code == 404, \
            f"Ожидался статус 404, но получен {response.status_code}: {response.json()}"

