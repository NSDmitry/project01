from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import SSOTestFlow

class TestUserInfo:
    # Тест на получение информации о пользователе
    def test_get_user_info(self, client: TestClient):
        auth_data = SSOTestFlow.sign_up_user(client)
        response = APIRouter.Users.current_user(client, auth_data.headers)

        assert response.status_code == 200, f"Ошибка: {response.json()}"
        assert response.json()["id"] == auth_data.user_id, f"Id пользователя не совпадает с ожидаемым"

    def test_unauthorized_access(self, client: TestClient):
        # Попытка получить информацию о пользователе без авторизации
        response = APIRouter.Users.current_user(client)

        assert response.status_code == 401, f"Ошибка: {response.status_code}: {response.json()}"
