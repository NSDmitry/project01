from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.mock_factories.AuthMockFactory import AuthMockFactory

class TestAuthLogout:
    # Тест на авторизацию
    def test_success_logout(self, client: TestClient):
        register_response = APIRouter.SSO.sign_up(client, AuthMockFactory.make_register_payload())
        session_id = register_response.json()["data"]["session_id"]

        current_user_response = APIRouter.Users.current_user(client, {"X-Session-Id": session_id})
        assert current_user_response.status_code == 200, \
            f"Ошибка при получении текущего пользователя: {current_user_response.json()}"

        logout_response = APIRouter.SSO.logout(client, {"X-Session-Id": session_id})
        assert logout_response.status_code == 200, \
            f"Ошибка при выходе из системы: {logout_response.json()}"

        logouted_user_response = APIRouter.Users.current_user(client, {"X-Session-Id": session_id})
        assert logouted_user_response.status_code == 401, \
            f"После выхода из системы пользователь не должен иметь доступ к текущему пользователю: {logouted_user_response.json()}"

    def test_double_logout(self, client: TestClient):
        register_response = APIRouter.SSO.sign_up(client, AuthMockFactory.make_register_payload())
        session_id = register_response.json()["data"]["session_id"]

        logout_response = APIRouter.SSO.logout(client, {"X-Session-Id": session_id})
        assert logout_response.status_code == 200, \
            f"Ошибка при выходе из системы: {logout_response.json()}"
        second_logout_response = APIRouter.SSO.logout(client, {"X-Session-Id": session_id})
        assert second_logout_response.status_code == 200, \
            f"Повторный выход из системы должен быть идемпотентным: {second_logout_response.json()}"

    def test_logout_without_session_header(self, client: TestClient):
        response = APIRouter.SSO.logout(client, {})
        assert response.status_code == 401, \
            f"Без X-Session-Id должен возвращаться 401: {response.json()}"

    def test_logout_with_invalid_session_header_is_idempotent(self, client: TestClient):
        response = APIRouter.SSO.logout(client, {"X-Session-Id": "invalid-session-id"})
        assert response.status_code == 200, \
            f"Logout с несуществующей сессией должен быть идемпотентным: {response.json()}"
