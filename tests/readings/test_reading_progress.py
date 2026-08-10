from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import ReadingFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, ReadingFlow


def _club_with_reading(api):
    owner = AuthFlow.register(api)
    club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
    reading = ReadingFlow.create(api, club_id, owner).json()["data"]

    return owner, club_id, reading


class TestReadingProgress:
    def test_member_marks_stage(self, api):
        owner, club_id, reading = _club_with_reading(api)
        first_stage = reading["stages"][0]

        response = api.set_reading_progress(
            reading["id"], {"stage_id": first_stage["id"]}, headers=owner.headers
        )
        progress = response.json()["data"]

        assert_status_code(response, 200)
        assert progress["stage"]["position"] == 1
        assert progress["user"]["id"] == owner.user_id
        # Срок первого этапа уже прошёл, и он закрыт - участник в графике.
        assert progress["on_track"] is True

    def test_page_resolves_to_stage(self, api):
        owner, club_id, reading = _club_with_reading(api)

        response = api.set_reading_progress(reading["id"], {"page": 150}, headers=owner.headers)
        progress = response.json()["data"]

        assert_status_code(response, 200)
        # 150-я страница закрывает первый этап (100), но не второй (200).
        assert progress["stage"]["position"] == 1
        assert progress["page"] == 150

    def test_page_before_first_stage_leaves_progress_without_stage(self, api):
        owner, club_id, reading = _club_with_reading(api)

        response = api.set_reading_progress(reading["id"], {"page": 10}, headers=owner.headers)
        progress = response.json()["data"]

        assert_status_code(response, 200)
        assert progress["stage"] is None
        assert progress["on_track"] is False

    def test_repeated_progress_updates_the_same_row(self, api, db):
        owner, club_id, reading = _club_with_reading(api)
        stages = reading["stages"]

        api.set_reading_progress(reading["id"], {"stage_id": stages[0]["id"]}, headers=owner.headers)
        response = api.set_reading_progress(
            reading["id"], {"stage_id": stages[1]["id"]}, headers=owner.headers
        )

        assert_status_code(response, 200)
        assert response.json()["data"]["stage"]["position"] == 2
        assert db.execute(text("SELECT count(*) FROM reading_progress")).scalar() == 1

    def test_stage_of_another_reading_is_rejected(self, api):
        owner, club_id, reading = _club_with_reading(api)
        other_owner = AuthFlow.register(api)
        other_club_id = BookclubFlow.create(api, auth=other_owner).json()["data"]["id"]
        other_reading = ReadingFlow.create(api, other_club_id, other_owner, volume_id="vol-2").json()["data"]

        response = api.set_reading_progress(
            reading["id"], {"stage_id": other_reading["stages"][0]["id"]}, headers=owner.headers
        )

        assert_status_code(response, 404)

    def test_non_member_cannot_mark_progress(self, api):
        owner, club_id, reading = _club_with_reading(api)
        stranger = AuthFlow.register(api)

        response = api.set_reading_progress(
            reading["id"], {"stage_id": reading["stages"][0]["id"]}, headers=stranger.headers
        )

        assert_status_code(response, 403)

    def test_empty_progress_is_rejected(self, api):
        owner, club_id, reading = _club_with_reading(api)

        response = api.set_reading_progress(reading["id"], {}, headers=owner.headers)

        assert_status_code(response, 422)

    def test_progress_of_finished_reading_is_rejected(self, api):
        owner, club_id, reading = _club_with_reading(api)
        api.finish_reading(reading["id"], headers=owner.headers)

        response = api.set_reading_progress(reading["id"], {"page": 50}, headers=owner.headers)

        assert_status_code(response, 409)

    def test_progress_list_shows_members_and_on_track_flag(self, api):
        owner, club_id, reading = _club_with_reading(api)
        member = MemberFlow.join(api, club_id)
        api.set_reading_progress(
            reading["id"], {"stage_id": reading["stages"][0]["id"]}, headers=owner.headers
        )
        api.set_reading_progress(reading["id"], {"page": 10}, headers=member.headers)

        response = api.reading_progress(reading["id"], headers=owner.headers)
        page = response.json()["data"]

        assert_status_code(response, 200)
        assert page["total"] == 2
        by_user = {item["user"]["id"]: item for item in page["items"]}
        assert by_user[owner.user_id]["on_track"] is True
        assert by_user[member.user_id]["on_track"] is False

    def test_everyone_is_on_track_before_first_deadline(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        # Все сроки впереди - отставать пока не от чего.
        payload = ReadingFactory.payload(stages=[ReadingFactory.stage(due_in_days=5, end_page=100)])
        reading = ReadingFlow.create(api, club_id, owner, payload).json()["data"]
        api.set_reading_progress(reading["id"], {"page": 10}, headers=owner.headers)

        response = api.reading_progress(reading["id"], headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["items"][0]["on_track"] is True

    def test_progress_of_unknown_reading_returns_404(self, api):
        owner = AuthFlow.register(api)

        response = api.reading_progress(999999, headers=owner.headers)

        assert_status_code(response, 404)

    def test_leaving_club_removes_progress(self, api, db):
        owner, club_id, reading = _club_with_reading(api)
        member = MemberFlow.join(api, club_id)
        api.set_reading_progress(
            reading["id"], {"stage_id": reading["stages"][0]["id"]}, headers=member.headers
        )

        api.leave_bookclub(club_id, headers=member.headers)

        assert db.execute(text("SELECT count(*) FROM reading_progress")).scalar() == 0

    def test_deleting_user_removes_progress(self, api, db):
        owner, club_id, reading = _club_with_reading(api)
        member = MemberFlow.join(api, club_id)
        api.set_reading_progress(
            reading["id"], {"stage_id": reading["stages"][0]["id"]}, headers=member.headers
        )

        api.delete_current_user(headers=member.headers, payload={"password": "ValidPass1"})

        assert db.execute(text("SELECT count(*) FROM reading_progress")).scalar() == 0
