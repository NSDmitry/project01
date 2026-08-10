from tests.support.assertions import assert_status_code
from tests.support.factories import ReadingFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, ReadingFlow


class TestCurrentReading:
    def test_current_reading_returns_summary(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        reading = ReadingFlow.create(api, club_id, owner).json()["data"]
        member = MemberFlow.join(api, club_id)
        api.set_reading_progress(
            reading["id"], {"stage_id": reading["stages"][0]["id"]}, headers=member.headers
        )

        response = api.current_reading(club_id, headers=owner.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        assert data["reading"]["id"] == reading["id"]
        assert data["reading"]["book"]["google_volume_id"] == "vol-1"
        # Из двух участников этап закрыл один.
        assert data["progress"]["members_count"] == 2
        assert data["progress"]["on_track_count"] == 1
        assert data["progress"]["on_track_ratio"] == 0.5
        assert data["progress"]["current_stage"]["position"] == 1

    def test_current_stage_is_empty_before_first_deadline(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        payload = ReadingFactory.payload(stages=[ReadingFactory.stage(due_in_days=5)])
        ReadingFlow.create(api, club_id, owner, payload)

        response = api.current_reading(club_id, headers=owner.headers)
        progress = response.json()["data"]["progress"]

        assert_status_code(response, 200)
        assert progress["current_stage"] is None
        assert progress["on_track_ratio"] == 1.0

    def test_no_current_reading_returns_404(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = api.current_reading(club_id, headers=owner.headers)

        assert_status_code(response, 404)

    def test_finished_reading_is_not_current(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        reading_id = ReadingFlow.create(api, club_id, owner).json()["data"]["id"]
        api.finish_reading(reading_id, headers=owner.headers)

        response = api.current_reading(club_id, headers=owner.headers)

        assert_status_code(response, 404)


class TestClubCardReading:
    def test_club_card_shows_current_reading(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        ReadingFlow.create(api, club_id, owner)

        response = api.bookclub(club_id, headers=owner.headers)
        current = response.json()["data"]["current_reading"]

        assert_status_code(response, 200)
        assert current["book"]["title"] == "Мастер и Маргарита"
        # Срок первого этапа прошёл, владелец ничего не отметил - никто не в графике.
        assert current["on_track_ratio"] == 0.0

    def test_club_card_ratio_grows_with_progress(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        reading = ReadingFlow.create(api, club_id, owner).json()["data"]
        api.set_reading_progress(
            reading["id"], {"stage_id": reading["stages"][0]["id"]}, headers=owner.headers
        )

        response = api.bookclub(club_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["current_reading"]["on_track_ratio"] == 1.0

    def test_club_without_reading_has_no_current_reading(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = api.bookclub(club_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["current_reading"] is None

    def test_club_list_carries_current_reading(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        ReadingFlow.create(api, club_id, owner)

        response = api.bookclubs(headers=owner.headers)
        items = response.json()["data"]["items"]

        assert_status_code(response, 200)
        assert items[0]["current_reading"]["id"] is not None
