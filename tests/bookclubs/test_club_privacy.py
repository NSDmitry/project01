from tests.support.assertions import assert_status_code
from tests.support.factories import BookclubFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestClubPrivacy:
    def test_club_is_public_by_default(self, api):
        auth = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=auth)

        assert created.json()["data"]["privacy"] == "public"

    def test_club_can_be_created_closed(self, api):
        auth = AuthFlow.register(api)
        created = BookclubFlow.create(
            api, auth=auth, payload=BookclubFactory.payload(privacy="by_request")
        )

        assert_status_code(created, 201)
        assert created.json()["data"]["privacy"] == "by_request"

    def test_join_rejected_for_by_request_club(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(
            api, auth=owner, payload=BookclubFactory.payload(privacy="by_request")
        ).json()["data"]["id"]
        outsider = AuthFlow.register(api)

        response = api.join_bookclub(club_id, headers=outsider.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "В этот клуб можно вступить только по заявке"

    def test_join_rejected_for_by_invite_club(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(
            api, auth=owner, payload=BookclubFactory.payload(privacy="by_invite")
        ).json()["data"]["id"]
        outsider = AuthFlow.register(api)

        response = api.join_bookclub(club_id, headers=outsider.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "В этот клуб можно вступить только по приглашению"

    def test_owner_can_close_open_club(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        updated = api.update_bookclub(club_id, {"privacy": "by_invite"}, headers=owner.headers)
        assert_status_code(updated, 200)
        assert updated.json()["data"]["privacy"] == "by_invite"

        outsider = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=outsider.headers), 403)

    def test_privacy_survives_unrelated_update(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(
            api, auth=owner, payload=BookclubFactory.payload(privacy="by_request")
        ).json()["data"]["id"]

        updated = api.update_bookclub(club_id, {"description": "Новое описание"}, headers=owner.headers)

        assert updated.json()["data"]["privacy"] == "by_request"

    def test_unknown_privacy_is_rejected(self, api):
        auth = AuthFlow.register(api)
        response = BookclubFlow.create(
            api, auth=auth, payload=BookclubFactory.payload(privacy="secret")
        )

        assert_status_code(response, 422)

    def test_privacy_changed_only_by_owner(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)

        assert_status_code(
            api.update_bookclub(club_id, {"privacy": "by_invite"}, headers=member.headers), 403
        )
