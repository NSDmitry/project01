from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow

class TestBookclubMemberships:
    def test_owner_is_member_of_created_bookclub(self, api):
        auth = AuthFlow.register(api)
        response = BookclubFlow.create(api, auth=auth)
        club_id = response.json()["data"]["id"]

        assert_status_code(response, 201)
        members = api.bookclub_members(club_id, headers=auth.headers)
        assert [member["id"] for member in members.json()["data"]["items"]] == [auth.user_id]

    def test_user_can_join_bookclub(self, api):
        owner = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=owner)
        club_id = created.json()["data"]["id"]
        member = AuthFlow.register(api)

        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        members = api.bookclub_members(club_id, headers=member.headers)
        assert member.user_id in [m["id"] for m in members.json()["data"]["items"]]

    def test_user_can_leave_bookclub(self, api):
        owner = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=owner)
        club_id = created.json()["data"]["id"]
        member = AuthFlow.register(api)

        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        assert_status_code(api.leave_bookclub(club_id, headers=member.headers), 200)

        members = api.bookclub_members(club_id, headers=member.headers)
        assert member.user_id not in [m["id"] for m in members.json()["data"]["items"]]

    def test_join_bookclub_returns_not_found_for_unknown_club(self, api):
        auth = AuthFlow.register(api)
        response = api.join_bookclub(999999, headers=auth.headers)
        assert_status_code(response, 404)
        assert response.json()["message"] == "Книжный клуб с таким id не найден"

    def test_leave_bookclub_returns_not_found_for_unknown_club(self, api):
        auth = AuthFlow.register(api)
        response = api.leave_bookclub(999999, headers=auth.headers)
        assert_status_code(response, 404)
        assert response.json()["message"] == "Книжный клуб с таким id не найден"

    def test_join_bookclub_rejects_duplicate_membership(self, api):
        owner = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=owner)
        member = AuthFlow.register(api)

        assert_status_code(api.join_bookclub(created.json()["data"]["id"], headers=member.headers), 200)
        assert_status_code(api.join_bookclub(created.json()["data"]["id"], headers=member.headers), 409)

    def test_leave_bookclub_rejects_non_member(self, api):
        owner = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=owner)
        outsider = AuthFlow.register(api)

        assert_status_code(api.leave_bookclub(created.json()["data"]["id"], headers=outsider.headers), 409)

    def test_owner_can_leave_bookclub(self, api):
        auth = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=auth)
        club_id = created.json()["data"]["id"]

        assert_status_code(api.leave_bookclub(club_id, headers=auth.headers), 200)

        members = api.bookclub_members(club_id, headers=auth.headers)
        assert auth.user_id not in [m["id"] for m in members.json()["data"]["items"]]

    def test_members_are_paginated_with_summary(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        second = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=second.headers), 200)

        page = api.bookclub_members(club_id, headers=owner.headers, params={"limit": 1, "offset": 0})
        data = page.json()["data"]

        assert_status_code(page, 200)
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert set(data["items"][0].keys()) == {"id", "name"}

    def test_join_bookclub_requires_authorization(self, api):
        created = BookclubFlow.create(api)
        assert_status_code(api.join_bookclub(created.json()["data"]["id"], headers={}), 401)

    def test_leave_bookclub_requires_authorization(self, api):
        created = BookclubFlow.create(api)
        assert_status_code(api.leave_bookclub(created.json()["data"]["id"], headers={}), 401)
