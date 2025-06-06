from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import SSOTestFlow, AuthenticatedUser

class TestPublicUserInfo:
    def test_public_user_info(self, client: TestClient):
        # Попытка получить публичную информацию о пользователе
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)

        user_id = auth_data.user_id
        public_response = APIRouter.Users.public_user_info(client, user_id, headers=auth_data.headers)

        assert public_response.status_code == 200, \
            f"Ошибка: {public_response.json()}"
        assert public_response.json()["data"]["id"] == user_id, \
            f"ИД пользователя в публичной информации не совпадает с ожидаемым"

    def test_private_data_in_public_info(self, client: TestClient):
        # Проверка, что приватные данные не возвращаются в публичной информации
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)

        user_id = auth_data.user_id

        another_auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        public_response = APIRouter.Users.public_user_info(client, user_id, another_auth_data.headers)

        assert "access_token" not in public_response.json()["data"], \
            f"Публичная информация не должна содержать access_token"
        assert "password" not in public_response.json()["data"], \
            f"Публичная информация не должна содержать пароль"
        assert "name" in public_response.json()["data"], \
            f"Публичная информация должна содержать имя пользователя"
        assert "phone_number" in public_response.json()["data"], \
            f"Публичная информация должна содержать номер телефона пользователя"
        assert "id" in public_response.json()["data"], \
            f"Публичная информация должна содержать ID пользователя"

    def test_public_info_unauthorized(self, client: TestClient):
        # Попытка получить публичную информацию о пользователе без авторизации
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)

        response = APIRouter.Users.public_user_info(client, auth_data.user_id)

        assert response.status_code == 401, \
            f"Ошибка: {response.status_code}: {response.json()}"