from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow


class TestCurrentUser:
    def test_current_user_returns_authenticated_user(self, api):
        auth = AuthFlow.register(api)
        response = api.current_user(auth.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["id"] == auth.user_id

    def test_current_user_requires_authorization(self, api):
        assert_status_code(api.current_user(), 401)
