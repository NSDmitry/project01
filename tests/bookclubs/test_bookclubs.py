import pytest
from faker import Faker
from fastapi.testclient import TestClient
from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import AuthenticatedUser, SSOTestFlow
from tests.utils.flows.BookclubFlow import BookclubFlow
from tests.utils.mock_factories.BookclubPayloadFactory import BookclubPayloadFactory

faker = Faker()

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

    @pytest.mark.parametrize("name", ["", faker.pystr(min_chars=1, max_chars=3), faker.pystr(min_chars=100, max_chars=200), 1])
    def test_create_bookc_club__name_validation_error(self, client: TestClient, name):
        # Тест на валидацию названия при создании клуба с некорректными данными (имя должно быть от 3 до 100 символов)
        payload = BookclubPayloadFactory.create_bookclub_payload(name=name, description=faker.pystr(min_chars=3, max_chars=500))
        response = BookclubFlow.create_bookclub(client, payload=payload)

        assert response.status_code == 422, f"Ожидался статус 422, но получен {response.status_code}: {response.json()}"

    @pytest.mark.parametrize("description", ["", faker.pystr(min_chars=1, max_chars=3), faker.pystr(min_chars=500, max_chars=1000), 1])
    def test_create_bookc_club__description_validation_error(self, client: TestClient, description):
        # Тест на валидацию описания при создании клуба с некорректными данными (описание должно быть от 3 до 500 символов)
        payload = BookclubPayloadFactory.create_bookclub_payload(name=faker.pystr(min_chars=3, max_chars=100), description=description)
        response = BookclubFlow.create_bookclub(client, payload=payload)

        assert response.status_code == 422, f"Ожидался статус 422, но получен {response.status_code}: {response.json()}"

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

    def test_get_bookclub_by_id(self, client: TestClient):
        # Тест на получение клуба по ID
        create_response = BookclubFlow.create_bookclub(client)

        club_id = create_response.json()["data"]["id"]
        response = APIRouter.BookClubs.get_book_club_by_id(client, club_id)

        assert response.status_code == 200, f"Ошибка при получении клуба по ID: {response.json()}"
        assert response.json()["data"]["id"] == club_id, "ID клуба не совпадает с ожидаемым"

    def test_get_bookclub_by_id_not_found(self, client: TestClient):
        # Тест на получение клуба по несуществующему ID
        response = APIRouter.BookClubs.get_book_club_by_id(client, club_id=999999)

        assert response.status_code == 404, f"Ожидался статус 404, но получен {response.status_code}: {response.json()}"