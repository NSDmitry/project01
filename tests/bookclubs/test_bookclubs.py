from fastapi.testclient import TestClient
from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import AuthenticatedUser, SSOTestFlow
from tests.utils.flows.BookclubFlow import BookclubFlow
from tests.utils.mock_factories.BookclubPayloadFactory import BookclubPayloadFactory

class TestAllClubs:
    def test_empty_clubs_list(self, client: TestClient):
        # Тест на получение списка клубов, когда нет ни одного клуба
        response = APIRouter.BookClubs.get_all_book_clubs(client)

        assert response.status_code == 200, f"Ошибка при получении списка клубов: {response.json()}"
        assert response.json()["data"] == [], "Список клубов должен быть пустым"

    def test_get_all_clubs(self, client: TestClient):
        # Тест на получение всех клубов
        BookclubFlow.create_bookclub(client)
        response = APIRouter.BookClubs.get_all_book_clubs(client)

        assert response.status_code == 200, f"Ошибка при получении списка клубов: {response.json()}"
        assert len(response.json()["data"]) > 0, "Список клубов не должен быть пустым"

    def test_create_book_club(self, client: TestClient):
        # Тест на создание клуба
        payload = BookclubPayloadFactory.create_bookclub_payload()
        response = BookclubFlow.create_bookclub(client, payload=payload)

        assert response.status_code == 201, f"Ошибка при создании клуба: {response.json()}"
        assert response.json()["data"]["name"] == payload["name"], "Имя клуба не совпадает с ожидаемым"
        assert response.json()["data"]["description"] == payload["description"], "Описание клуба не совпадает с ожидаемым"

    def test_user_is_owner_of_created_club(self, client: TestClient):
        # Тест на проверку, что пользователь является владельцем созданного клуба
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = BookclubFlow.create_bookclub(client, auth_data=auth_data)

        assert response.status_code == 201, f"Ошибка при создании клуба: {response.json()}"
        assert response.json()["data"]["owner_id"] == auth_data.user_id, "ID владельца клуба не совпадает с ожидаемым"

    def test_user_is_member_of_created_club(self, client: TestClient):
        # Тест на проверку, что пользователь является участником созданного клуба
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = BookclubFlow.create_bookclub(client, auth_data)

        assert response.status_code == 201, f"Ошибка при создании клуба: {response.json()}"
        assert auth_data.user_id in response.json()["data"]["members_ids"], "ID владельца клуба должен быть в списке участников"

    def test_get_owned_bookclubs(self, client: TestClient):
        # Тест на получение клубов, которыми владеет пользователь
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        BookclubFlow.create_bookclub(client, auth_data=auth_data)

        response = APIRouter.BookClubs.get_owned_book_clubs(client, headers=auth_data.headers)

        assert response.status_code == 200, f"Ошибка при получении списка клубов: {response.json()}"
        assert all(club["owner_id"] == auth_data.user_id for club in response.json()["data"]), "Все клубы должны принадлежать авторизованному пользователю"