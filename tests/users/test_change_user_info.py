from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import SSOTestFlow
from tests.utils.mock_factories.UsersPayloadFactory import UsersPayloadFactory
from tests.utils.mock_factories.SSOMockFactory import SSOMockFactory

class TestChangeUserInfo:
    def test_change_current_user_phone_number_and_name(self, client: TestClient):
        # Тест на изменение номера телефона и имени текущего пользователя
        user_name = "username"
        phone_number = SSOMockFactory.generate_random_phone_number()

        auth_data = SSOTestFlow.sign_up_user(client)

        new_user_name = "new username"
        new_phone_number = SSOMockFactory.generate_random_phone_number()

        payload = UsersPayloadFactory.make_change_user_info_payload(new_user_name, new_phone_number)
        response = APIRouter.Users.change_current_user_info(client, payload, auth_data.headers)

        assert response.status_code == 200, f"Ошибка при изменении информации о пользователе: {response.json()}, payload: {payload}"

        assert response.json()["data"]["name"] != user_name, f"Имя пользователя не было изменено. Ожидалось: {new_user_name}, получено: {response.json()['name']}"
        assert str(response.json()["data"]["phone_number"]) != str(phone_number), f"Номер телефона не был изменен. Ожидалось: {new_phone_number}, получено: {response.json()['phone_number']}"

        assert response.json()["data"]["name"] == new_user_name, f"Имя пользователя не совпадает с ожидаемым. Ожидалось: {new_user_name}, получено: {response.json()['name']}"
        assert str(response.json()["data"]["phone_number"]) == str(new_phone_number), f"Номер телефона не совпадает с ожидаемым. Ожидалось: {new_phone_number}, получено: {response.json()['phone_number']}"

    def test_change_only_user_phone(self, client: TestClient):
        # Тест на изменение только номера телефона текущего пользователя
        user_name = "username"
        phone_number = SSOMockFactory.generate_random_phone_number()

        auth_data = SSOTestFlow.sign_up_user(client)

        new_phone_number = SSOMockFactory.generate_random_phone_number()

        payload = UsersPayloadFactory.make_change_user_info_payload(user_name, new_phone_number)
        response = APIRouter.Users.change_current_user_info(client, payload, auth_data.headers)

        assert response.status_code == 200, f"Ошибка при изменении информации о пользователе: {response.json()}, payload: {payload}"

        assert str(response.json()["data"]["phone_number"]) != str(phone_number), f"Номер телефона не был изменен. Ожидалось: {new_phone_number}, получено: {response.json()['phone_number']}"
        assert response.json()["data"]["name"] == user_name, f"Имя пользователя было изменено. Ожидалось: {user_name}, получено: {response.json()['name']}"
        assert str(response.json()["data"]["phone_number"]) == str(new_phone_number), f"Номер телефона не совпадает с ожидаемым. Ожидалось: {new_phone_number}, получено: {response.json()['phone_number']}"

    def test_change_only_user_name(self, client: TestClient):
        # Тест на изменение только имени текущего пользователя
        user_name = "username"
        phone_number = SSOMockFactory.generate_random_phone_number()

        auth_data = SSOTestFlow.sign_up_user(client)

        new_user_name = "new username"

        payload = UsersPayloadFactory.make_change_user_info_payload(new_user_name, phone_number)
        response = APIRouter.Users.change_current_user_info(client, payload, auth_data.headers)

        assert response.status_code == 200, f"Ошибка при изменении информации о пользователе: {response.json()}, payload: {payload}"

        assert response.json()["data"]["name"] != user_name, f"Имя пользователя не было изменено. Ожидалось: {new_user_name}, получено: {response.json()['name']}"
        assert str(response.json()["data"]["phone_number"]) == str(phone_number), f"Номер телефона был изменен. Ожидалось: {phone_number}, получено: {response.json()['phone_number']}"
        assert response.json()["data"]["name"] == new_user_name, f"Имя пользователя не совпадает с ожидаемым. Ожидалось: {new_user_name}, получено: {response.json()['name']}"