from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow, NominationFlow
from tests.support.google_books import install_fake_google


class TestNominationCreate:
    def test_member_nominates_book(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        response = NominationFlow.create(api, club_id, member)
        nomination = response.json()["data"]

        assert_status_code(response, 201)
        assert nomination["club_id"] == club_id
        assert nomination["book"]["google_volume_id"] == "vol-1"
        assert nomination["votes_count"] == 0
        assert nomination["voted"] is False

    def test_same_book_cannot_be_nominated_twice(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        NominationFlow.create(api, club_id, owner)

        response = NominationFlow.create(api, club_id, owner)

        assert_status_code(response, 409)
        assert db.execute(text("SELECT count(*) FROM book_nominations")).scalar() == 1

    def test_non_member_cannot_nominate(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        stranger = AuthFlow.register(api)

        response = NominationFlow.create(api, club_id, stranger)

        assert_status_code(response, 403)

    def test_unknown_volume_id_returns_404(self, api, db):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        install_fake_google([])

        response = api.nominate_book(
            club_id, {"book_volume_id": "no-such-volume"}, headers=owner.headers
        )

        assert_status_code(response, 404)
        assert db.execute(text("SELECT count(*) FROM book_nominations")).scalar() == 0

    def test_unknown_club_returns_404(self, api):
        user = AuthFlow.register(api)

        response = NominationFlow.create(api, 999999, user)

        assert_status_code(response, 404)

    def test_nominations_are_listed_in_order(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        NominationFlow.create(api, club_id, owner, volume_id="vol-1")
        NominationFlow.create(api, club_id, owner, volume_id="vol-2")

        response = api.nominations(club_id, headers=owner.headers)
        nominations = response.json()["data"]

        assert_status_code(response, 200)
        assert [nomination["book"]["google_volume_id"] for nomination in nominations] == [
            "vol-1",
            "vol-2",
        ]

    def test_nominations_require_auth(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        assert_status_code(api.nominations(club_id), 401)
