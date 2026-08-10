from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import ReadingFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, ReadingFlow
from tests.support.google_books import install_fake_google, suggestion


class TestReadingCreate:
    def test_owner_creates_reading_with_stages(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = ReadingFlow.create(api, club_id, owner)
        reading = response.json()["data"]

        assert_status_code(response, 201)
        assert reading["club_id"] == club_id
        assert reading["book"]["google_volume_id"] == "vol-1"
        assert reading["finished_at"] is None
        # Позиции этапов расставляет сервер по порядку в запросе.
        assert [stage["position"] for stage in reading["stages"]] == [1, 2]
        assert [stage["title"] for stage in reading["stages"]] == ["Главы 1-5", "Главы 6-10"]
        assert reading["stages"][0]["end_page"] == 100

    def test_reading_without_stages_is_allowed(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = ReadingFlow.create(api, club_id, owner, ReadingFactory.payload(stages=[]))

        assert_status_code(response, 201)
        assert response.json()["data"]["stages"] == []

    def test_member_cannot_create_reading(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        response = ReadingFlow.create(api, club_id, member)

        assert_status_code(response, 403)

    def test_second_active_reading_is_rejected(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        ReadingFlow.create(api, club_id, owner)

        response = ReadingFlow.create(api, club_id, owner)

        assert_status_code(response, 409)
        assert db.execute(text("SELECT count(*) FROM readings")).scalar() == 1

    def test_reading_can_be_created_after_previous_one_is_finished(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        reading_id = ReadingFlow.create(api, club_id, owner).json()["data"]["id"]
        api.finish_reading(reading_id, headers=owner.headers)

        response = ReadingFlow.create(api, club_id, owner, volume_id="vol-2")

        assert_status_code(response, 201)

    def test_unknown_volume_id_returns_404(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        install_fake_google([])

        response = api.create_reading(
            club_id, ReadingFactory.payload(book_volume_id="no-such-volume"), headers=owner.headers
        )

        assert_status_code(response, 404)
        assert db.execute(text("SELECT count(*) FROM readings")).scalar() == 0

    def test_unknown_club_returns_404(self, api):
        owner = AuthFlow.register(api)
        install_fake_google([suggestion(volume_id="vol-1")])

        response = api.create_reading(999999, ReadingFactory.payload(), headers=owner.headers)

        assert_status_code(response, 404)

    def test_deadline_before_start_is_rejected(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = ReadingFlow.create(
            api, club_id, owner, ReadingFactory.payload(started_in_days=5, deadline_in_days=1, stages=[])
        )

        assert_status_code(response, 422)

    def test_stage_outside_of_reading_dates_is_rejected(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        payload = ReadingFactory.payload(stages=[ReadingFactory.stage(due_in_days=30)])

        response = ReadingFlow.create(api, club_id, owner, payload)

        assert_status_code(response, 422)

    def test_stage_dates_must_grow(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        payload = ReadingFactory.payload(
            stages=[ReadingFactory.stage(due_in_days=5), ReadingFactory.stage(due_in_days=1)]
        )

        response = ReadingFlow.create(api, club_id, owner, payload)

        assert_status_code(response, 422)

    def test_stage_pages_must_grow(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        payload = ReadingFactory.payload(
            stages=[
                ReadingFactory.stage(due_in_days=1, end_page=200),
                ReadingFactory.stage(due_in_days=5, end_page=100),
            ]
        )

        response = ReadingFlow.create(api, club_id, owner, payload)

        assert_status_code(response, 422)

    def test_deleting_club_removes_its_readings(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        ReadingFlow.create(api, club_id, owner)

        api.delete_bookclub(club_id, headers=owner.headers)

        assert db.execute(text("SELECT count(*) FROM readings")).scalar() == 0
        assert db.execute(text("SELECT count(*) FROM reading_stages")).scalar() == 0
