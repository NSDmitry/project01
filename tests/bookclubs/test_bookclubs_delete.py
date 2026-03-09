from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow

class TestBookclubsDelete:
    def test_delete_bookclub_removes_entity(self, api):
        auth = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=auth)
        club_id = created.json()["data"]["id"]

        response = api.delete_bookclub(club_id, headers=auth.headers)
        assert_status_code(response, 200)
        assert response.json()["message"] == "Книжный клуб успешно удален"
        assert_status_code(api.bookclub(club_id, headers=auth.headers), 404)

    def test_delete_bookclub_returns_not_found_for_unknown_id(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.delete_bookclub(999999, headers=auth.headers), 404)

    def test_delete_bookclub_requires_authorization(self, api):
        assert_status_code(api.delete_bookclub(1, headers={}), 401)

    def test_delete_bookclub_requires_owner_role(self, api):
        owner = AuthFlow.register(api)
        created = BookclubFlow.create(api, auth=owner)
        outsider = AuthFlow.register(api)

        response = api.delete_bookclub(created.json()["data"]["id"], headers=outsider.headers)
        assert_status_code(response, 403)
        assert response.json()["message"] == "Пользователь не является владельцем книжного клуба"
