from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.mock_factories.AuthMockFactory import AuthMockFactory

class TestAuthLogin:
    # Тест на авторизацию
    def test_success_login(self, client: TestClient):
        sign_up_payload = AuthMockFactory.make_register_payload()
        APIRouter.SSO.sign_up(client, sign_up_payload)

        sign_in_payload = AuthMockFactory.make_login_payload(sign_up_payload["phone_number"], sign_up_payload["password"])
        sign_in_response = APIRouter.SSO.sign_in(client, sign_in_payload)

        assert sign_in_response.status_code == 200, \
            f"Ошибка при авторизации пользователя: {sign_in_response.json()}"
        assert "session_id" in sign_in_response.json()["data"], \
            f"Ответ должен содержать session_id"

    # Тест авторизации на проверку неверного пароля
    def test_login_wrong_password(self, client: TestClient):
        sign_up_payload = AuthMockFactory.make_register_payload()
        APIRouter.SSO.sign_up(client, sign_up_payload)

        wrong_password_payload = AuthMockFactory.make_login_payload(sign_up_payload["phone_number"], "wrong_password")
        sign_in_response = APIRouter.SSO.sign_in(client, wrong_password_payload)

        assert sign_in_response.status_code == 401, \
            f"Пользователь должен получить ошибку, что пароль не верный: {sign_in_response.json()}"

    # Тест авторизации на проверку неверного номера телефона
    def test_login_wrong_phone_number(self, client: TestClient):
        sign_up_payload = AuthMockFactory.make_register_payload()
        APIRouter.SSO.sign_up(client, sign_up_payload)

        wrong_phone_number_payload = AuthMockFactory.make_login_payload("12312312", sign_up_payload["password"])
        sign_in_response = APIRouter.SSO.sign_in(client, wrong_phone_number_payload)

        assert sign_in_response.status_code == 404, \
            f"Пользователь должен получить ошибку, что номер телефона не найден: {sign_in_response.json()}"