from typing import Dict
from fastapi.testclient import TestClient
import uuid

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

def sign_up_user(client: TestClient, payload: Dict):
    """
    Зарегистрировать пользователя через /signup
    """
    return post_json(client, "/api/SSO/signup", payload)

def sign_in_user(client: TestClient, payload: Dict):
    """
    Авторизовать пользователя через /signin
    """
    return post_json(client, "/api/SSO/signin", payload)