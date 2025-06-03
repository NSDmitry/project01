from dataclasses import dataclass
from typing import Dict
from fastapi.testclient import TestClient
import uuid

@dataclass
class AuthenticatedUser:
    access_token: str
    headers: Dict[str, str]
    phone_number: str
    user_id: int

def make_sign_up_payload(name: str = "Тестовый пользователь", phone_number: str = None, password: str = "123456"):
    return {
        "name": name,
        "phone_number": phone_number or str(_generate_random_phone_number()),
        "password": password
    }

def make_sign_in_payload(phone_number: str, password: str):
    return {
        "phone_number": phone_number,
        "password": password
    }

def _generate_random_phone_number() -> int:
    """
    Генератор тестового номера телефона — гарантирует уникальность
    """
    return "79" + str(uuid.uuid4().int)[0:9]

def post_json(client: TestClient, url: str, json_data: Dict):
    """
    Упрощённый post-запрос с json и возвратом response
    """
    return client.post(url, json=json_data)

def sign_up_user(client: TestClient, payload=None):
    """
    Зарегистрировать пользователя через /signup
    """
    if payload is None:
        payload = make_sign_up_payload()

    return post_json(client, "/api/SSO/signup", payload)

def sign_in_user(client: TestClient, payload: Dict):
    """
    Авторизовать пользователя через /signin
    """
    return post_json(client, "/api/SSO/signin", payload)

def register_and_login_user(client: TestClient) -> AuthenticatedUser:
    """
    Регистрирует и авторизует пользователя, возвращает AuthenticatedUser
    """
    # Создаём payload с уникальным номером
    signup_payload = make_sign_up_payload()
    sign_up_response = sign_up_user(client, signup_payload)

    assert sign_up_response.status_code == 201, f"Signup failed: {sign_up_response.json()}"

    # Авторизуемся
    signin_payload = make_sign_in_payload(
        phone_number=signup_payload["phone_number"],
        password=signup_payload["password"]
    )
    sign_in_response = sign_in_user(client, signin_payload)
    assert sign_in_response.status_code == 200, f"Signin failed: {sign_in_response.json()}"

    data = sign_in_response.json()["data"]
    access_token = data["access_token"]
    token_type = data.get("token_type", "Bearer")

    return AuthenticatedUser(
        access_token=access_token,
        headers={"Authorization": f"{token_type} {access_token}"},
        phone_number=signup_payload["phone_number"],
        user_id=data.get("id"),
    )