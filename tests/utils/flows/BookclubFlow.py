from starlette.testclient import TestClient

from tests.APIRouter import APIRouter
from tests.utils.flows.SSOFlow import AuthenticatedUser, SSOTestFlow
from tests.utils.mock_factories.BookclubPayloadFactory import BookclubPayloadFactory

class BookclubFlow:
    @staticmethod
    def create_bookclub(client: TestClient, auth_data: AuthenticatedUser = None, payload=None):
        # Создание клуба с использованием авторизованного пользователя
        # Если auth_data не передан, то создаем нового пользователя

        if auth_data is None:
            auth_data = SSOTestFlow.sign_up_user(client)

        if payload is None:
            payload = BookclubPayloadFactory.create_bookclub_payload()

        return APIRouter.BookClubs.create_book_club(client, payload, auth_data.headers)


