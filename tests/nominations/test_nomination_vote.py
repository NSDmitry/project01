from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, NominationFlow


def _nominate_two(api, club_id, member):
    first = NominationFlow.create(api, club_id, member, volume_id="vol-1").json()["data"]["id"]
    second = NominationFlow.create(api, club_id, member, volume_id="vol-2").json()["data"]["id"]

    return first, second


class TestNominationVote:
    def test_member_votes(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]

        response = api.vote(nomination_id, headers=owner.headers)
        nomination = response.json()["data"]

        assert_status_code(response, 200)
        assert nomination["votes_count"] == 1
        assert nomination["voted"] is True

    def test_repeated_vote_does_not_double_count(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]

        api.vote(nomination_id, headers=owner.headers)
        response = api.vote(nomination_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["votes_count"] == 1
        assert db.execute(text("SELECT count(*) FROM nomination_votes")).scalar() == 1

    def test_vote_moves_between_nominations(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        first, second = _nominate_two(api, club_id, owner)

        api.vote(first, headers=owner.headers)
        api.vote(second, headers=owner.headers)

        counts = {
            nomination["id"]: nomination["votes_count"]
            for nomination in api.nominations(club_id, headers=owner.headers).json()["data"]
        }
        assert counts == {first: 0, second: 1}

    def test_votes_of_different_members_add_up(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]

        api.vote(nomination_id, headers=owner.headers)
        response = api.vote(nomination_id, headers=member.headers)

        assert response.json()["data"]["votes_count"] == 2

    def test_voted_flag_is_personal(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]
        api.vote(nomination_id, headers=owner.headers)

        nominations = api.nominations(club_id, headers=member.headers).json()["data"]

        assert nominations[0]["votes_count"] == 1
        assert nominations[0]["voted"] is False

    def test_non_member_cannot_vote(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]
        stranger = AuthFlow.register(api)

        response = api.vote(nomination_id, headers=stranger.headers)

        assert_status_code(response, 403)

    def test_vote_for_unknown_nomination_returns_404(self, api):
        user = AuthFlow.register(api)

        assert_status_code(api.vote(999999, headers=user.headers), 404)

    def test_unvote_removes_vote(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]
        api.vote(nomination_id, headers=owner.headers)

        response = api.unvote(nomination_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["votes_count"] == 0
        assert response.json()["data"]["voted"] is False
        assert db.execute(text("SELECT count(*) FROM nomination_votes")).scalar() == 0

    def test_unvote_without_vote_returns_409(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]

        assert_status_code(api.unvote(nomination_id, headers=owner.headers), 409)

    def test_unvote_after_moving_vote_away_returns_409(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        first, second = _nominate_two(api, club_id, owner)
        api.vote(first, headers=owner.headers)
        api.vote(second, headers=owner.headers)

        assert_status_code(api.unvote(first, headers=owner.headers), 409)

    def test_leaving_club_takes_the_vote_away(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]
        api.vote(nomination_id, headers=member.headers)

        api.leave_bookclub(club_id, headers=member.headers)

        nominations = api.nominations(club_id, headers=owner.headers).json()["data"]
        assert nominations[0]["votes_count"] == 0

    def test_deleted_user_takes_the_vote_away(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        nomination_id = NominationFlow.create(api, club_id, owner).json()["data"]["id"]
        api.vote(nomination_id, headers=member.headers)

        api.delete_current_user(headers=member.headers, payload={"password": "ValidPass1"})

        nominations = api.nominations(club_id, headers=owner.headers).json()["data"]
        assert nominations[0]["votes_count"] == 0
