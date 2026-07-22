import pytest

from tests.support.assertions import assert_status_code
from tests.support.factories import AuthFactory, UserFactory
from tests.support.flows import AuthFlow


class TestNameValidation:
    @pytest.mark.parametrize("invalid_name", ["", "   ", "x" * 101])
    def test_register_rejects_invalid_name(self, api, invalid_name):
        response = api.register(AuthFactory.register_payload(name=invalid_name))

        assert_status_code(response, 422)
        body = response.json()
        assert body["success"] is False
        assert body["errors"]

    def test_register_strips_name(self, api):
        payload = AuthFactory.register_payload(name="  Test User  ")
        session_id = api.register(payload).json()["data"]["session_id"]

        current = api.current_user(headers={"X-Session-Id": session_id}).json()["data"]
        assert current["name"] == "Test User"

    def test_update_user_rejects_empty_name(self, api):
        auth = AuthFlow.register(api)
        payload = UserFactory.update_payload(name="", phone_number=auth.phone_number)

        assert_status_code(api.update_user(payload, headers=auth.headers), 422)

    def test_public_user_rejects_id_above_int64(self, api):
        auth = AuthFlow.register(api)
        response = api.public_user(99999999999999999999999, headers=auth.headers)

        assert_status_code(response, 422)
