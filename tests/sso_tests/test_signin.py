from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.sso_utils import make_sign_up_payload, sign_up_user, sign_in_user, make_sign_in_payload

class TestSignIn:
    # Тест на авторизацию
    def test_sign_in(self, client: TestClient):
        sign_up_payload = make_sign_up_payload()
        APIRouter.SSO.sign_up(client, sign_up_payload)

        sign_in_payload = make_sign_in_payload(sign_up_payload["phone_number"], sign_up_payload["password"])
        sign_in_response = APIRouter.SSO.sign_in(client, sign_in_payload)

        assert sign_in_response.status_code == 200
        assert "access_token" in sign_in_response.json()["data"]

    # Тест авторизации на проверку неверного пароля
    def test_sign_in_wrong_password(self, client: TestClient):
        sign_up_payload = make_sign_up_payload()
        APIRouter.SSO.sign_up(client, sign_up_payload)

        wrong_password_payload = make_sign_in_payload(sign_up_payload["phone_number"], "wrong_password")
        sign_in_response = APIRouter.SSO.sign_in(client, wrong_password_payload)

        assert sign_in_response.status_code == 401

    # Тест авторизации на проверку неверного номера телефона
    def test_sign_in_wrong_phone_number(self, client: TestClient):
        sign_up_payload = make_sign_up_payload()
        APIRouter.SSO.sign_up(client, sign_up_payload)

        wrong_phone_number_payload = make_sign_in_payload("12312312", sign_up_payload["password"])
        sign_in_response = sign_in_user(client, wrong_phone_number_payload)

        assert sign_in_response.status_code == 404