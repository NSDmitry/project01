from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import BookclubFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow


def _closed_club(api, owner):
    return BookclubFlow.create(
        api, auth=owner, payload=BookclubFactory.payload(privacy="by_invite")
    ).json()["data"]["id"]


class TestClubInvites:
    def test_owner_creates_invite(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)

        response = api.create_invite(club_id, headers=owner.headers)

        assert_status_code(response, 201)
        data = response.json()["data"]
        assert data["club_id"] == club_id
        assert data["code"]
        assert data["expires_at"] is None

    def test_invite_lets_user_into_closed_club(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)
        code = api.create_invite(club_id, headers=owner.headers).json()["data"]["code"]
        guest = AuthFlow.register(api)

        response = api.join_by_invite(code, headers=guest.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["members_count"] == 2
        members = api.bookclub_members(club_id, headers=owner.headers)
        assert guest.user_id in [member["id"] for member in members.json()["data"]["items"]]

    def test_moderator_creates_invite(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)
        moderator = MemberFlow.moderator(api, club_id, owner)

        assert_status_code(api.create_invite(club_id, headers=moderator.headers), 201)

    def test_plain_member_cannot_create_invite(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)
        member = MemberFlow.join_by_invite(api, club_id, owner)

        response = api.create_invite(club_id, headers=member.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "Создавать приглашения может владелец или модератор клуба"

    def test_outsider_cannot_create_invite(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)
        outsider = AuthFlow.register(api)

        assert_status_code(api.create_invite(club_id, headers=outsider.headers), 403)

    def test_unknown_code_is_not_found(self, api):
        guest = AuthFlow.register(api)

        response = api.join_by_invite("no-such-code", headers=guest.headers)

        assert_status_code(response, 404)
        assert response.json()["message"] == "Приглашение не найдено"

    def test_expired_invite_is_rejected(self, api, db):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)
        code = api.create_invite(club_id, {"expires_in_days": 1}, headers=owner.headers).json()["data"]["code"]

        # Отматываем срок в прошлое: ждать сутки в тесте нечем.
        db.execute(
            text("UPDATE club_invites SET expires_at = now() - interval '1 day' WHERE code = :code"),
            {"code": code},
        )
        db.commit()

        guest = AuthFlow.register(api)
        response = api.join_by_invite(code, headers=guest.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "Срок действия приглашения истёк"

    def test_invite_with_expiry_returns_deadline(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)

        response = api.create_invite(club_id, {"expires_in_days": 7}, headers=owner.headers)

        assert response.json()["data"]["expires_at"] is not None

    def test_invite_rejects_repeated_join(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)
        code = api.create_invite(club_id, headers=owner.headers).json()["data"]["code"]
        guest = AuthFlow.register(api)

        assert_status_code(api.join_by_invite(code, headers=guest.headers), 200)
        assert_status_code(api.join_by_invite(code, headers=guest.headers), 409)

    def test_invite_dies_with_its_club(self, api):
        owner = AuthFlow.register(api)
        club_id = _closed_club(api, owner)
        code = api.create_invite(club_id, headers=owner.headers).json()["data"]["code"]

        assert_status_code(api.delete_bookclub(club_id, headers=owner.headers), 200)

        guest = AuthFlow.register(api)
        assert_status_code(api.join_by_invite(code, headers=guest.headers), 404)
