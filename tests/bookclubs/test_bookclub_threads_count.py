from tests.support.assertions import assert_status_code
from tests.support.factories import ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestBookclubThreadsCount:
    """threads_count клуба правит домен тредов прямым вызовом change_threads_count
    в транзакции создания/удаления треда."""

    def test_threads_count_tracks_create_and_delete(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        assert api.bookclub(club_id, headers=owner.headers).json()["data"]["threads_count"] == 0

        first = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title="Первый"), headers=owner.headers
        )
        api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title="Второй"), headers=owner.headers
        )
        assert api.bookclub(club_id, headers=owner.headers).json()["data"]["threads_count"] == 2

        thread_id = first.json()["data"]["id"]
        assert_status_code(api.delete_thread(thread_id, headers=owner.headers), 200)
        assert api.bookclub(club_id, headers=owner.headers).json()["data"]["threads_count"] == 1
