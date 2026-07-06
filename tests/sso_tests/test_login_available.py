from tests.support.assertions import assert_status_code
from tests.support.factories import AuthFactory


class TestLoginAvailable:
    def test_registered_phone_is_available_for_login(self, api):
        signup_payload = AuthFactory.register_payload()
        api.register(signup_payload)

        response = api.login_available({"phone_number": signup_payload["phone_number"]})

        assert_status_code(response, 200)
        assert response.json()["data"]["is_registered"] is True

    def test_unknown_phone_is_available_for_registration(self, api):
        response = api.login_available({"phone_number": AuthFactory.phone_number()})

        assert_status_code(response, 200)
        assert response.json()["data"]["is_registered"] is False

    def test_validates_phone_number_format(self, api):
        response = api.login_available({"phone_number": "not-a-phone"})

        assert_status_code(response, 422)
