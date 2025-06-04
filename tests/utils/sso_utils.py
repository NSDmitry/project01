from dataclasses import dataclass
from typing import Dict
from fastapi.testclient import TestClient
import uuid

from tests.APIRouter import APIRouter


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
    return "79" + str(uuid.uuid4().int)[0:9]

def post_json(client: TestClient, url: str, json_data: Dict):
    return client.post(url, json=json_data)

def sign_up_user(client: TestClient, payload=None) -> AuthenticatedUser:
    """
    Зарегистрировать пользователя через /signup
    """
    if payload is None:
        payload = make_sign_up_payload()

    response = APIRouter.SSO.sign_up(client, payload)

    data = response.json()["data"]
    access_token = data["access_token"]
    token_type = data.get("token_type", "Bearer")

    return AuthenticatedUser(
        access_token=access_token,
        headers={"Authorization": f"{token_type} {access_token}"},
        phone_number=data.get("phone_number"),
        user_id=data.get("id"),
    )

def sign_in_user(client: TestClient, payload: Dict):
    """
    Авторизовать пользователя через /signin
    """
    return post_json(client, "/api/SSO/signin", payload)