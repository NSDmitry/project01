import pytest
from fastapi.testclient import TestClient
from tests.utils.sso_utils import make_sign_up_payload, sign_up_user, sign_in_user, make_sign_in_payload

class TestSignUp:
    # Тест на регистрацию пользователя
    def test_sign_up(self, client: TestClient):
        payload = make_sign_up_payload()
        response = sign_up_user(client, payload)

        assert response.status_code == 201

    # Тест на проверку полей после регистрации
    def test_sign_up_fields(self, client: TestClient):
        payload = make_sign_up_payload()
        response = sign_up_user(client, payload)
        data = response.json()["data"]

        assert data["phone_number"] == int(payload["phone_number"])
        assert data["name"] == payload["name"]

    # Тест на проверку, что нельзя зарегистрировать пользователя с уже существующим номером телефона
    def test_sing_up_exist(self, client: TestClient):
        user_payload = make_sign_up_payload()
        sign_up_user(client, user_payload)

        response = sign_up_user(client, user_payload)
        assert response.status_code == 409

    # Тест на валидацию номера телефона
    @pytest.mark.parametrize("invalid_phone", ["test", "-1", 123.4, 112312312312312312])
    def test_sign_up_phone_number(self, client: TestClient, invalid_phone):
        payload = make_sign_up_payload(phone_number=invalid_phone)
        response = sign_up_user(client, payload)

        assert response.status_code == 422
