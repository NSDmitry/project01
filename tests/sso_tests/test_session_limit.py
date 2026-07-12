from tests.support.assertions import assert_status_code
from tests.support.factories import AuthFactory


class TestSessionLimit:
    def test_sixth_session_evicts_oldest(self, api):
        signup_payload = AuthFactory.register_payload()
        register_response = api.register(signup_payload)
        sids = [register_response.json()["data"]["session_id"]]

        login_payload = AuthFactory.login_payload(
            phone_number=signup_payload["phone_number"],
            password=signup_payload["password"],
        )
        for _ in range(5):
            sids.append(api.login(login_payload).json()["data"]["session_id"])

        # Всего создано 6 сессий, лимит 5: самая старая (регистрационная) вытеснена.
        assert_status_code(api.current_user(headers={"X-Session-Id": sids[0]}), 401)
        for sid in sids[1:]:
            assert_status_code(api.current_user(headers={"X-Session-Id": sid}), 200)
