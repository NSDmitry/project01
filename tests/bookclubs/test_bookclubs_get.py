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

    def test_list_owned_bookclubs_returns_only_owned_clubs(self, api):
        auth = AuthFlow.register(api)
        BookclubFlow.create(api, auth=auth)
        response = api.owned_bookclubs(headers=auth.headers)

        assert_status_code(response, 200)
        assert all(club["owner_id"] == auth.user_id for club in response.json()["data"])

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
