import pytest
from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.mock_factories.SSOMockFactory import SSOMockFactory

class TestSignUp:
    # Тест на регистрацию пользователя
    def test_sign_up(self, client: TestClient):
        response = APIRouter.SSO.sign_up(client, SSOMockFactory.make_sign_up_payload())

        assert response.status_code == 201, f"Ошибка при регистрации пользователя: {response.json()}"

    # Тест на проверку полей после регистрации
    def test_sign_up_fields(self, client: TestClient):
        payload = SSOMockFactory.make_sign_up_payload()
        response = APIRouter.SSO.sign_up(client, payload)
        data = response.json()["data"]

        assert data["phone_number"] == int(payload["phone_number"]), \
            f"Номер телефона не совпадает: {data['phone_number']} != {payload['phone_number']}"
        assert data["name"] == payload["name"], \
            f"Имя пользователя не совпадает: {data['name']} != {payload['name']}"

    # Тест на проверку, что нельзя зарегистрировать пользователя с уже существующим номером телефона
    def test_sign_up_exist(self, client: TestClient):
        payload = SSOMockFactory.make_sign_up_payload()
        APIRouter.SSO.sign_up(client, payload)

        response = APIRouter.SSO.sign_up(client, payload)
        assert response.status_code == 409, \
            f"Нельзя зарегистрировать пользователя с уже существующим номером телефона: {response.json()}"

    # Тест на валидацию номера телефона
    @pytest.mark.parametrize("invalid_phone", ["test", "-1", 123.4, 112312312312312312])
    def test_sign_up_phone_number(self, client: TestClient, invalid_phone):
        payload = SSOMockFactory.make_sign_up_payload(phone_number=invalid_phone)
        response = APIRouter.SSO.sign_up(client, payload)

        assert response.status_code == 422
