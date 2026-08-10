from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import ReadingFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, NominationFlow, ReadingFlow


class TestVotingClose:
    def test_winner_becomes_the_reading(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        NominationFlow.create(api, club_id, owner, volume_id="vol-1")
        winner_id = NominationFlow.create(api, club_id, owner, volume_id="vol-2").json()["data"]["id"]
        api.vote(winner_id, headers=member.headers)

        response = api.close_voting(club_id, ReadingFactory.schedule_payload(), headers=owner.headers)
        reading = response.json()["data"]

        assert_status_code(response, 201)
        assert reading["book"]["google_volume_id"] == "vol-2"
        assert reading["finished_at"] is None
        assert [stage["position"] for stage in reading["stages"]] == [1, 2]

    def test_close_clears_nominations_and_votes(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]
        api.vote(nomination_id, headers=owner.headers)

        api.close_voting(club_id, ReadingFactory.schedule_payload(), headers=owner.headers)

        assert api.nominations(club_id, headers=owner.headers).json()["data"] == []
        assert db.execute(text("SELECT count(*) FROM nomination_votes")).scalar() == 0

    def test_tie_is_won_by_the_earlier_nomination(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        first = NominationFlow.create(api, club_id, owner, volume_id="vol-1").json()["data"]["id"]
        second = NominationFlow.create(api, club_id, owner, volume_id="vol-2").json()["data"]["id"]
        api.vote(first, headers=owner.headers)
        api.vote(second, headers=member.headers)

        response = api.close_voting(club_id, ReadingFactory.schedule_payload(), headers=owner.headers)

        assert response.json()["data"]["book"]["google_volume_id"] == "vol-1"

    def test_nomination_without_votes_can_win_alone(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        NominationFlow.create(api, club_id, owner)

        response = api.close_voting(club_id, ReadingFactory.schedule_payload(), headers=owner.headers)

        assert_status_code(response, 201)
        assert response.json()["data"]["book"]["google_volume_id"] == "vol-1"

    def test_member_cannot_close_voting(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        NominationFlow.create(api, club_id, owner)

        response = api.close_voting(club_id, ReadingFactory.schedule_payload(), headers=member.headers)

        assert_status_code(response, 403)
        assert db.execute(text("SELECT count(*) FROM book_nominations")).scalar() == 1

    def test_close_without_nominations_returns_409(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = api.close_voting(club_id, ReadingFactory.schedule_payload(), headers=owner.headers)

        assert_status_code(response, 409)
        assert db.execute(text("SELECT count(*) FROM readings")).scalar() == 0

    def test_close_with_active_reading_returns_409_and_keeps_nominations(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        ReadingFlow.create(api, club_id, owner)
        NominationFlow.create(api, club_id, owner, volume_id="vol-2")

        response = api.close_voting(club_id, ReadingFactory.schedule_payload(), headers=owner.headers)

        assert_status_code(response, 409)
        assert db.execute(text("SELECT count(*) FROM book_nominations")).scalar() == 1
        assert db.execute(text("SELECT count(*) FROM readings")).scalar() == 1

    def test_invalid_schedule_returns_422(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        NominationFlow.create(api, club_id, owner)

        response = api.close_voting(
            club_id,
            ReadingFactory.schedule_payload(started_in_days=10, deadline_in_days=-10, stages=[]),
            headers=owner.headers,
        )

        assert_status_code(response, 422)

    def test_unknown_club_returns_404(self, api):
        owner = AuthFlow.register(api)

        response = api.close_voting(999999, ReadingFactory.schedule_payload(), headers=owner.headers)

        assert_status_code(response, 404)

    def test_club_deletion_takes_nominations_away(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]
        api.vote(nomination_id, headers=owner.headers)

        api.delete_bookclub(club_id, headers=owner.headers)

        assert db.execute(text("SELECT count(*) FROM book_nominations")).scalar() == 0
        assert db.execute(text("SELECT count(*) FROM nomination_votes")).scalar() == 0
