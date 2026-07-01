from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow

class TestAllClubs:
    def test_list_bookclubs_requires_authorization(self, api):
        assert_status_code(api.bookclubs(), 401)

    def test_list_bookclubs_returns_empty_list_for_new_user(self, api):
        auth = AuthFlow.register(api)
        response = api.bookclubs(headers=auth.headers)

        assert_status_code(response, 200)
        assert response.json()["data"] == []

    def test_list_bookclubs_returns_created_clubs(self, api):
        auth = AuthFlow.register(api)
        BookclubFlow.create(api, auth=auth)
        response = api.bookclubs(headers=auth.headers)

        assert_status_code(response, 200)
        assert len(response.json()["data"]) > 0

    def test_list_bookclubs_relation_owner_returns_only_owned_clubs(self, api):
        auth = AuthFlow.register(api)
        BookclubFlow.create(api, auth=auth)
        BookclubFlow.create(api)
        response = api.bookclubs(headers=auth.headers, relation="owner")

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert len(data) == 1
        assert all(club["owner"]["id"] == auth.user_id for club in data)

    def test_list_bookclubs_relation_member_returns_joined_clubs(self, api):
        owner_auth = AuthFlow.register(api)
        own_club = BookclubFlow.create(api, auth=owner_auth)
        own_club_id = own_club.json()["data"]["id"]

        member_auth = AuthFlow.register(api)
        joined = BookclubFlow.create(api)
        joined_club_id = joined.json()["data"]["id"]
        api.join_bookclub(joined_club_id, headers=member_auth.headers)

        response = api.bookclubs(headers=member_auth.headers, relation="member")

        assert_status_code(response, 200)
        club_ids = {club["id"] for club in response.json()["data"]}
        assert club_ids == {joined_club_id}
        assert own_club_id not in club_ids

    def test_list_bookclubs_relation_member_includes_owned_clubs(self, api):
        auth = AuthFlow.register(api)
        own_club = BookclubFlow.create(api, auth=auth)
        own_club_id = own_club.json()["data"]["id"]

        response = api.bookclubs(headers=auth.headers, relation="member")

        assert_status_code(response, 200)
        club_ids = {club["id"] for club in response.json()["data"]}
        assert own_club_id in club_ids

    def test_list_bookclubs_rejects_invalid_relation(self, api):
        auth = AuthFlow.register(api)
        response = api.bookclubs(headers=auth.headers, relation="stranger")

        assert_status_code(response, 422)

    def test_get_bookclub_returns_requested_entity(self, api):
        auth = AuthFlow.register(api)
        created = BookclubFlow.create(api)
        club_id = created.json()["data"]["id"]

        response = api.bookclub(club_id, headers=auth.headers)
        assert_status_code(response, 200)
        assert response.json()["data"]["id"] == club_id

    def test_get_bookclub_requires_authorization(self, api):
        created = BookclubFlow.create(api)
        club_id = created.json()["data"]["id"]
        assert_status_code(api.bookclub(club_id), 401)

    def test_get_bookclub_returns_not_found_for_unknown_id(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.bookclub(999999, headers=auth.headers), 404)
