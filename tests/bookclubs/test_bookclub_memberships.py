from fastapi.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import AuthenticatedUser, SSOTestFlow
from tests.utils.flows.BookclubFlow import BookclubFlow

class TestBookclubMemberships:
    def test_user_is_member_of_created_club(self, client: TestClient):
        # Тест на проверку, что пользователь является участником созданного клуба
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = BookclubFlow.create_bookclub(client, auth_data=auth_data)

        assert response.status_code == 201, \
            f"Ошибка при создании клуба: {response.json()}"
        assert response.json()["data"]["members_ids"][0] == auth_data.user_id, \
            "ID участника клуба не совпадает с ожидаемым"

    def test_user_can_join_bookclub(self, client: TestClient):
        # Тест на проверку, что пользователь может присоединиться к клубу
        # Первый пользователь создает клуб, а второй пользователь присоединяется к нему

        auth_data1: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_response = BookclubFlow.create_bookclub(client, auth_data=auth_data1)
        club_id = create_response.json()["data"]["id"]

        auth_data2: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        join_response = APIRouter.BookClubs.join_book_club(client, club_id, auth_data2.headers)

        assert join_response.status_code == 200, \
            f"Ошибка при присоединении к клубу: {join_response.json()}"
        assert auth_data2.user_id in join_response.json()["data"]["members_ids"], \
            f"Пользователь не был добавлен в список участников клуба. {join_response.json()}"

    def test_user_can_leave_bookclub(self, client: TestClient):
        # Тест на проверку, что пользователь может покинуть клуб
        # Первый пользователь создает клуб, а второй пользователь присоединяется к нему и покидает его

        auth_data1: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_response = BookclubFlow.create_bookclub(client, auth_data=auth_data1)
        club_id = create_response.json()["data"]["id"]

        auth_data2: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        join_response = APIRouter.BookClubs.join_book_club(client, club_id, auth_data2.headers)

        assert join_response.status_code == 200, \
            f"Ошибка при присоединении к клубу: {join_response.json()}"

        leave_response = APIRouter.BookClubs.leave_book_club(client, club_id, auth_data2.headers)

        assert leave_response.status_code == 200, \
            f"Ошибка при выходе из клуба: {leave_response.json()}"
        assert auth_data2.user_id not in leave_response.json()["data"]["members_ids"], \
            "Пользователь не был удален из списка участников клуба"

    def test_user_cannot_join_nonexistent_bookclub(self, client: TestClient):
        # Тест на проверку, что пользователь не может присоединиться к несуществующему клубу
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = APIRouter.BookClubs.join_book_club(client, club_id=999999, headers=auth_data.headers)

        assert response.status_code == 404, \
            f"Ожидался статус 404, но получен {response.status_code}: {response.json()}"
        assert response.json()["message"] == "Книжный клуб с таким id не найден", \
            "Сообщение об ошибке не совпадает с ожидаемым"

    def test_user_cannot_leave_nonexistent_bookclub(self, client: TestClient):
        # Тест на проверку, что пользователь не может покинуть несуществующий клуб
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        response = APIRouter.BookClubs.leave_book_club(client, club_id=999999, headers=auth_data.headers)

        assert response.status_code == 404, \
            f"Ожидался статус 404, но получен {response.status_code}: {response.json()}"
        assert response.json()["message"] == "Книжный клуб с таким id не найден", \
            "Сообщение об ошибке не совпадает с ожидаемым"

    def test_user_cannot_join_bookclub_twice(self, client: TestClient):
        # Тест на проверку, что пользователь не может присоединиться к клубу дважды
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_response = BookclubFlow.create_bookclub(client, auth_data=auth_data)
        club_id = create_response.json()["data"]["id"]

        auth_data2: AuthenticatedUser = SSOTestFlow.sign_up_user(client)

        join_response = APIRouter.BookClubs.join_book_club(client, club_id, auth_data2.headers)
        join_response2 = APIRouter.BookClubs.join_book_club(client, club_id, auth_data2.headers)

        assert join_response2.status_code == 409, \
            f"Ошибка при присоединении к клубу, в котором уже пользователь состоит: {join_response.json()}"

    def test_user_cannot_leave_bookclub_if_not_member(self, client: TestClient):
        # Тест на проверку, что пользователь не может покинуть клуб, в котором он не состоит
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_bookclub_response = BookclubFlow.create_bookclub(client, auth_data=auth_data)
        club_id = create_bookclub_response.json()["data"]["id"]

        auth_data2: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        leave_response = APIRouter.BookClubs.leave_book_club(client, club_id, auth_data2.headers)

        assert leave_response.status_code == 409, \
            f"Ожидался статус 409, но получен {leave_response.status_code}: {leave_response.json()}"

    def test_user_can_leave_bookclub_as_owner(self, client: TestClient):
        # Тест на проверку, что владелец клуба может покинуть клуб
        auth_data: AuthenticatedUser = SSOTestFlow.sign_up_user(client)
        create_response = BookclubFlow.create_bookclub(client, auth_data=auth_data)
        club_id = create_response.json()["data"]["id"]

        leave_response = APIRouter.BookClubs.leave_book_club(client, club_id, auth_data.headers)

        assert leave_response.status_code == 200, \
            f"Ошибка при выходе из клуба владельцем: {leave_response.json()}"
        assert auth_data.user_id not in leave_response.json()["data"]["members_ids"], \
            "Владелец клуба не был удален из списка участников клуба"