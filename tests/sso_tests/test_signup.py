import pytest

from tests.support.assertions import assert_contains_keys, assert_status_code
from tests.support.factories import AuthFactory


class TestSignUp:
    def test_register_returns_created_user(self, api):
        response = api.register(AuthFactory.register_payload())
        assert_status_code(response, 201)

    def test_register_returns_expected_fields(self, api):
        payload = AuthFactory.register_payload()
        response = api.register(payload)
        data = response.json()["data"]

        assert_contains_keys(data, {"id", "name", "phone_number", "session_id", "created_at"})
        assert data["phone_number"] == int(payload["phone_number"])
        assert data["name"] == payload["name"]

    def test_register_rejects_existing_phone_number(self, api):
        payload = AuthFactory.register_payload()
        api.register(payload)

        response = api.register(payload)
        assert_status_code(response, 409)

    @pytest.mark.parametrize("invalid_phone", ["test", "-1", 123.4, 112312312312312312])
    def test_register_validates_phone_number(self, api, invalid_phone):
        payload = AuthFactory.register_payload(phone_number=invalid_phone)
        response = api.register(payload)

        assert_status_code(response, 422)
