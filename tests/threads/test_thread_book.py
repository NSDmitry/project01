from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow
from tests.support.google_books import install_fake_google, suggestion


def _thread_payload(club_id: int, volume_id: str | None = None) -> dict:
    payload = ThreadFactory.create_payload(club_id=club_id)
    if volume_id is not None:
        payload["book_volume_id"] = volume_id
    return payload


class TestThreadBook:
    def test_create_thread_with_book(self, api):
        install_fake_google([suggestion(volume_id="vol-1")])
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = api.create_thread(_thread_payload(club_id, "vol-1"), headers=owner.headers)
        book = response.json()["data"]["book"]

        assert_status_code(response, 201)
        assert book["google_volume_id"] == "vol-1"
        assert book["title"] == "Мастер и Маргарита"
        assert book["author"] == "Михаил Булгаков"
        assert book["published_year"] == 1967

    def test_create_thread_without_book(self, api):
        install_fake_google([])
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = api.create_thread(_thread_payload(club_id), headers=owner.headers)

        assert_status_code(response, 201)
        assert response.json()["data"]["book"] is None

    def test_book_is_deduplicated_by_volume_id(self, api, db):
        fake = install_fake_google([suggestion(volume_id="vol-1")])
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        first = api.create_thread(_thread_payload(club_id, "vol-1"), headers=owner.headers)
        second = api.create_thread(_thread_payload(club_id, "vol-1"), headers=owner.headers)

        assert_status_code(first, 201)
        assert_status_code(second, 201)
        assert first.json()["data"]["book"]["id"] == second.json()["data"]["book"]["id"]
        # Второй запрос берёт книгу из БД, а не ходит в Google.
        assert fake.get_volume_calls == 1
        assert db.execute(text("SELECT count(*) FROM books")).scalar() == 1

    def test_unknown_volume_id_returns_404(self, api, db):
        install_fake_google([])
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = api.create_thread(_thread_payload(club_id, "no-such-volume"), headers=owner.headers)

        assert_status_code(response, 404)
        # Тред не должен создаться.
        assert db.execute(text("SELECT count(*) FROM threads")).scalar() == 0
