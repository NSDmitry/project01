from tests.support.assertions import assert_status_code
from tests.support.factories import AuthFactory


class TestAuthLogin:
    def test_login_returns_session_id(self, api):
        signup_payload = AuthFactory.register_payload()
        api.register(signup_payload)

        login_payload = AuthFactory.login_payload(
            phone_number=signup_payload["phone_number"],
            password=signup_payload["password"],
        )
        response = api.login(login_payload)

        assert_status_code(response, 200)
        assert "session_id" in response.json()["data"]

    def test_login_rejects_wrong_password(self, api):
        signup_payload = AuthFactory.register_payload()
        api.register(signup_payload)

        response = api.login(
            AuthFactory.login_payload(
                phone_number=signup_payload["phone_number"],
                password="wrong_password",
            )
        )
        assert_status_code(response, 401)

    def test_login_rejects_unknown_phone_number(self, api):
        api.register(AuthFactory.register_payload())
        response = api.login(AuthFactory.login_payload(phone_number="12312312", password="123456"))
        assert_status_code(response, 404)

    def test_failed_login_does_not_authorize_user(self, api):
        signup_payload = AuthFactory.register_payload()
        api.register(signup_payload)

        response = api.login(
            AuthFactory.login_payload(
                phone_number=signup_payload["phone_number"],
                password="wrong_password",
            )
        )
        assert_status_code(response, 401)
        assert_status_code(api.current_user(), 401)
