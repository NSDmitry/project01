import time

from tests.support.assertions import assert_contains_keys, assert_status_code
from tests.support.factories import TelegramFactory


class TestTelegramAuth:
    def test_first_login_creates_user(self, api, telegram_bot_token):
        response = api.telegram({"init_data": TelegramFactory.init_data()})

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert_contains_keys(data, {"id", "name", "phone_number", "session_id", "created_at"})
        assert data["phone_number"] is None
        assert data["session_id"]

    def test_repeated_login_returns_same_user(self, api, telegram_bot_token):
        user = TelegramFactory.user()

        first = api.telegram({"init_data": TelegramFactory.init_data(user=user)})
        second = api.telegram({"init_data": TelegramFactory.init_data(user=user)})

        assert_status_code(second, 200)
        assert first.json()["data"]["id"] == second.json()["data"]["id"]
        assert first.json()["data"]["session_id"] != second.json()["data"]["session_id"]

    def test_session_authorizes_protected_endpoint(self, api, telegram_bot_token):
        login = api.telegram({"init_data": TelegramFactory.init_data()})
        sid = login.json()["data"]["session_id"]

        current = api.current_user(headers={"X-Session-Id": sid})
        assert_status_code(current, 200)

    def test_rejects_tampered_signature(self, api, telegram_bot_token):
        response = api.telegram({"init_data": TelegramFactory.init_data(tamper_hash=True)})
        assert_status_code(response, 401)

    def test_rejects_wrong_bot_token(self, api, telegram_bot_token):
        response = api.telegram({"init_data": TelegramFactory.init_data(bot_token="999:other-token")})
        assert_status_code(response, 401)

    def test_rejects_stale_auth_date(self, api, telegram_bot_token):
        stale = int(time.time()) - (25 * 60 * 60)
        response = api.telegram({"init_data": TelegramFactory.init_data(auth_date=stale)})
        assert_status_code(response, 401)

    def test_rejects_missing_init_data_field(self, api, telegram_bot_token):
        response = api.telegram({})
        assert_status_code(response, 422)

    def test_returns_500_when_bot_token_not_configured(self, api, telegram_bot_token_unset):
        response = api.telegram({"init_data": TelegramFactory.init_data()})
        assert_status_code(response, 500)
