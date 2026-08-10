from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, ReadingFlow


class TestReadingFinish:
    def test_owner_finishes_reading(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        reading_id = ReadingFlow.create(api, club_id, owner).json()["data"]["id"]

        response = api.finish_reading(reading_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["finished_at"] is not None

    def test_member_cannot_finish_reading(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        reading_id = ReadingFlow.create(api, club_id, owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        response = api.finish_reading(reading_id, headers=member.headers)

        assert_status_code(response, 403)

    def test_finishing_twice_is_rejected(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        reading_id = ReadingFlow.create(api, club_id, owner).json()["data"]["id"]
        api.finish_reading(reading_id, headers=owner.headers)

        response = api.finish_reading(reading_id, headers=owner.headers)

        assert_status_code(response, 409)

    def test_unknown_reading_returns_404(self, api):
        owner = AuthFlow.register(api)

        response = api.finish_reading(999999, headers=owner.headers)

        assert_status_code(response, 404)


class TestReadingArchive:
    def test_archive_lists_readings_newest_first(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        first_id = ReadingFlow.create(api, club_id, owner).json()["data"]["id"]
        api.finish_reading(first_id, headers=owner.headers)
        second_id = ReadingFlow.create(api, club_id, owner, volume_id="vol-2").json()["data"]["id"]

        response = api.readings(club_id, headers=owner.headers)
        page = response.json()["data"]

        assert_status_code(response, 200)
        assert page["total"] == 2
        assert [item["id"] for item in page["items"]] == [second_id, first_id]
        # Текущий заход отличается пустым finished_at.
        assert page["items"][0]["finished_at"] is None
        assert page["items"][1]["finished_at"] is not None
        assert page["items"][1]["stages"][0]["title"] == "Главы 1-5"

    def test_archive_of_unknown_club_returns_404(self, api):
        owner = AuthFlow.register(api)

        response = api.readings(999999, headers=owner.headers)

        assert_status_code(response, 404)
