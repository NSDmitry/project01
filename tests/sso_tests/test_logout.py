from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow


class TestAuthLogout:
    def test_logout_invalidates_active_session(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.current_user(auth.headers), 200)

        response = api.logout(auth.headers)
        assert_status_code(response, 200)
        assert_status_code(api.current_user(auth.headers), 401)

    def test_logout_is_idempotent(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.logout(auth.headers), 200)
        assert_status_code(api.logout(auth.headers), 200)

    def test_logout_requires_session_header(self, api):
        assert_status_code(api.logout({}), 401)

    def test_logout_with_unknown_session_is_idempotent(self, api):
        assert_status_code(api.logout({"X-Session-Id": "invalid-session-id"}), 200)
