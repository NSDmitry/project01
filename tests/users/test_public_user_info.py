from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow

class TestPublicUserInfo:
    def test_public_user_info_returns_requested_profile(self, api):
        auth = AuthFlow.register(api)
        response = api.public_user(auth.user_id, headers=auth.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["id"] == auth.user_id

    def test_public_user_info_hides_private_fields(self, api):
        auth = AuthFlow.register(api)
        another_auth = AuthFlow.register(api)
        response = api.public_user(auth.user_id, headers=another_auth.headers)
        data = response.json()["data"]

        assert "access_token" not in data
        assert "password" not in data
        assert "session_id" not in data
        assert {"id", "name", "phone_number"}.issubset(data.keys())

    def test_public_user_info_requires_authorization(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.public_user(auth.user_id), 401)
