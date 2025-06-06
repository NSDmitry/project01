import pytest
from faker import Faker
from fastapi.testclient import TestClient
from tests.utils.flows.SSOFlow import AuthenticatedUser, SSOTestFlow
from tests.utils.flows.BookclubFlow import BookclubFlow
from tests.utils.mock_factories.BookclubPayloadFactory import BookclubPayloadFactory

faker = Faker()

class TestBookclubsCreate:
    def test_create_book_club(self, client: TestClient):
        # Тест на создание клуба
        payload = BookclubPayloadFactory.create_bookclub_payload()
        response = BookclubFlow.create_bookclub(client, payload=payload)

        assert response.status_code == 201, \
            f"Ошибка при создании клуба: {response.json()}"
        assert response.json()["data"]["name"] == payload["name"], \
            "Имя клуба не совпадает с ожидаемым"
        assert response.json()["data"]["description"] == payload["description"], \
            f"Описание клуба не совпадает с ожидаемым"

    @pytest.mark.parametrize("name",
                             ["", faker.pystr(min_chars=0, max_chars=2), faker.pystr(min_chars=100, max_chars=200), 1])
    def test_create_bookc_club__name_validation_error(self, client: TestClient, name):
        # Тест на валидацию названия при создании клуба с некорректными данными (имя должно быть от 3 до 100 символов)
        payload = BookclubPayloadFactory.create_bookclub_payload(name=name,
                                                                 description=faker.pystr(min_chars=3, max_chars=500))
        response = BookclubFlow.create_bookclub(client, payload=payload)

        assert response.status_code == 422, \
            f"Ожидался статус 422, но получен {response.status_code}: {response.json()}"

    @pytest.mark.parametrize("description",
                             ["", faker.pystr(min_chars=0, max_chars=2), faker.pystr(min_chars=501, max_chars=1000), 1])
    def test_create_bookc_club__description_validation_error(self, client: TestClient, description):
        # Тест на валидацию описания при создании клуба с некорректными данными (описание должно быть от 3 до 500 символов)
        payload = BookclubPayloadFactory.create_bookclub_payload(name=faker.pystr(min_chars=3, max_chars=100),
                                                                 description=description)
        response = BookclubFlow.create_bookclub(client, payload=payload)

        assert response.status_code == 422, \
            f"Ожидался статус 422, но получен {response.status_code}: {response.json()}"

    def test_user_is_owner_of_created_club(self, client: TestClient):
        # Тест на проверку, что пользователь является владельцем созданного клуба
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = BookclubFlow.create_bookclub(client, auth_data=auth_data)

        assert response.status_code == 201, \
            f"Ошибка при создании клуба: {response.json()}"
        assert response.json()["data"]["owner_id"] == auth_data.user_id, \
            f"ID владельца клуба не совпадает с ожидаемым"

    def test_user_is_member_of_created_club(self, client: TestClient):
        # Тест на проверку, что пользователь является участником созданного клуба
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = BookclubFlow.create_bookclub(client, auth_data)

        assert response.status_code == 201, \
            f"Ошибка при создании клуба: {response.json()}"
        assert auth_data.user_id in response.json()["data"]["members_ids"], \
            f"ID владельца клуба должен быть в списке участников"