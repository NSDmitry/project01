from starlette.testclient import TestClient
from tests.utils.sso_utils import AuthenticatedUser


def current_user(client: TestClient, auth_data: AuthenticatedUser):
    """
    Получить информацию о текущем пользователе.
    Возвращает словарь с данными пользователя.
    """
    return client.get("/api/users/current", headers=auth_data.headers)

def public_user_info(client: TestClient, user_id: int):
    """
    Получить публичную информацию о пользователе по ID.
    Возвращает словарь с данными пользователя.
    """
    return client.get(f"/api/users/public?user_id={user_id}")