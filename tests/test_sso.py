from fastapi.testclient import TestClient
from tests.utils.sso_utils import make_sign_up_payload, sign_up_user, sign_in_user, make_sign_in_payload


# Тест на регистрацию пользователя
def test_sign_up(client: TestClient):
    payload = make_sign_up_payload()
    response = sign_up_user(client, payload)

    assert response.status_code == 201
    assert str(response.json()["data"]["phone_number"]) == payload["phone_number"]
    assert response.json()["data"]["name"] == payload["name"]

    assert "id" in response.json()["data"]

# Тест на проверку, что нельзя зарегистрировать пользователя с уже существующим номером телефона
def test_sing_up_exist(client: TestClient):
    first_user = make_sign_up_payload(name="Test1", phone_number=79999999999, password="123123")
    second_user = make_sign_up_payload(name="Test2", phone_number=79999999999, password="123123")

    first_user_register_response = sign_up_user(client, first_user)
    assert first_user_register_response.status_code == 201

    second_user_register_response = sign_up_user(client, second_user)
    assert second_user_register_response.status_code == 409

# Тест на валидацию номера телефона
def test_sign_up_phone_number(client: TestClient):
    payload = make_sign_up_payload(phone_number="test")
    response = sign_up_user(client, payload)

    assert response.status_code == 422

# Тест на авторизацию
def test_sign_in(client: TestClient):
    sign_up_payload = make_sign_up_payload()
    sign_up_response = sign_up_user(client, sign_up_payload)

    sign_in_payload = make_sign_in_payload(sign_up_payload["phone_number"], sign_up_payload["password"])
    sign_in_response = sign_in_user(client, sign_in_payload)

    assert sign_in_response.status_code == 200
    assert "access_token" in sign_in_response.json()["data"]

# Тест авторизации на проверку неверного пароля
def test_sign_in_wrong_password(client: TestClient):
    sign_up_payload = make_sign_up_payload()
    sign_up_response = sign_up_user(client, sign_up_payload)

    wrong_password_payload = make_sign_in_payload(sign_up_payload["phone_number"], "wrong_password")
    sign_in_response = sign_in_user(client, wrong_password_payload)

    assert sign_in_response.status_code == 401

# Тест авторизации на проверку неверного номера телефона
def test_sign_in_wrong_phone_number(client: TestClient):
    sign_up_payload = make_sign_up_payload()
    sign_up_response = sign_up_user(client, sign_up_payload)

    wrong_phone_number_payload = make_sign_in_payload("12312312", sign_up_payload["password"])
    sign_in_response = sign_in_user(client, wrong_phone_number_payload)

    assert sign_in_response.status_code == 404

