from fastapi.testclient import TestClient
from tests.utils.flows.SSOFlow import AuthenticatedUser, SSOTestFlow
from tests.utils.flows.BookclubFlow import BookclubFlow
from tests.APIRouter import APIRouter

class TestBookclubsDelete:
    def test_delete_bookclub(self, client: TestClient):
        # Тест на удаление клуба
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_response = BookclubFlow.create_bookclub(client, auth_data )
        club_id = create_response.json()["data"]["id"]

        delete_response = APIRouter.BookClubs.delete_book_club(client, club_id, auth_data.headers)

        assert delete_response.status_code == 200, \
            f"Ошибка при удалении клуба: {delete_response.json()}"
        assert delete_response.json()["message"] == "Книжный клуб успешно удален", \
            "Сообщение об успешном удалении клуба не совпадает с ожидаемым"

        get_club_by_id_response = APIRouter.BookClubs.get_book_club_by_id(client, club_id, headers=auth_data.headers)

        assert get_club_by_id_response.status_code == 404, \
            f"Клуб должен быть удален, но он все еще существует: {get_club_by_id_response.json()}"

    def test_delete_bookclub_not_found(self, client: TestClient):
        # Тест на удаление клуба, который не существует
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = APIRouter.BookClubs.delete_book_club(client, club_id=999999, headers=auth_data.headers)

        assert response.status_code == 404, \
            f"Ожидался статус 404, но получен {response.status_code}: {response.json()}"

    def test_delete_bookclub_unauthorized(self, client: TestClient):
        # Тест на удаление клуба без авторизации
        response = APIRouter.BookClubs.delete_book_club(client, club_id=1, headers={})

        assert response.status_code == 401, \
            f"Ожидался статус 401, но получен {response.status_code}: {response.json()}"

    def test_delete_bookclub_forbidden(self, client: TestClient):
        # Тест на удаление клуба, когда пользователь не является владельцем
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_response = BookclubFlow.create_bookclub(client, auth_data=auth_data)
        club_id = create_response.json()["data"]["id"]

        another_user_auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = APIRouter.BookClubs.delete_book_club(client, club_id, another_user_auth_data.headers)

        assert response.status_code == 403, \
            f"Ожидался статус 403, но получен {response.status_code}: {response.json()}"
        assert response.json()["message"] == "Пользователь не является владельцем книжного клуба", \
            f"Сообщение об ошибке не совпадает с ожидаемым: {response.json()}"