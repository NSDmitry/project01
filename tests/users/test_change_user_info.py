from tests.support.assertions import assert_status_code
from tests.support.factories import AuthFactory, UserFactory
from tests.support.flows import AuthFlow

class TestChangeUserInfo:
    def test_update_user_name_and_phone_number(self, api):
        auth = AuthFlow.register(api)
        new_phone = AuthFactory.phone_number()
        payload = UserFactory.update_payload(name="New Name", phone_number=new_phone)

        response = api.update_user(payload, headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        assert data["name"] == "New Name"
        assert str(data["phone_number"]) == str(new_phone)

    def test_update_user_phone_only(self, api):
        auth = AuthFlow.register(api)
        new_phone = AuthFactory.phone_number()
        payload = UserFactory.update_payload(name="Test User", phone_number=new_phone)

        response = api.update_user(payload, headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        assert data["name"] == "Test User"
        assert str(data["phone_number"]) == str(new_phone)

    def test_update_user_name_only(self, api):
        auth = AuthFlow.register(api)
        payload = UserFactory.update_payload(name="Renamed User", phone_number=auth.phone_number)

        response = api.update_user(payload, headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        assert data["name"] == "Renamed User"
        assert str(data["phone_number"]) == str(auth.phone_number)

    def test_update_user_rejects_existing_phone_number(self, api):
        first_user = AuthFlow.register(api)
        second_user = AuthFlow.register(api)
        payload = UserFactory.update_payload(name="New Name", phone_number=second_user.phone_number)

        response = api.update_user(payload, headers=first_user.headers)
        assert_status_code(response, 409)

    def test_update_user_requires_authorization(self, api):
        payload = UserFactory.update_payload(name="New Name", phone_number=AuthFactory.phone_number())
        assert_status_code(api.update_user(payload, headers={}), 401)

    def test_change_password_logs_out_all_active_sessions(self, api):
        signup_payload = AuthFactory.register_payload(password="ValidPass1")
        first_session_response = api.register(signup_payload)
        first_headers = {"X-Session-Id": first_session_response.json()["data"]["session_id"]}

        second_session_response = api.login(
            AuthFactory.login_payload(
                phone_number=signup_payload["phone_number"],
                password=signup_payload["password"],
            )
        )
        second_headers = {"X-Session-Id": second_session_response.json()["data"]["session_id"]}

        response = api.change_password(
            UserFactory.change_password_payload(
                current_password="ValidPass1",
                new_password="NewValidPass1",
            ),
            headers=first_headers,
        )

        assert_status_code(response, 200)
        assert_status_code(api.current_user(first_headers), 401)
        assert_status_code(api.current_user(second_headers), 401)

    def test_change_password_rejects_wrong_current_password(self, api):
        signup_payload = AuthFactory.register_payload(password="ValidPass1")
        register_response = api.register(signup_payload)
        headers = {"X-Session-Id": register_response.json()["data"]["session_id"]}

        response = api.change_password(
            UserFactory.change_password_payload(
                current_password="WrongPass1",
                new_password="NewValidPass1",
            ),
            headers=headers,
        )

        assert_status_code(response, 401)

    def test_change_password_validates_password_policy(self, api):
        signup_payload = AuthFactory.register_payload(password="ValidPass1")
        register_response = api.register(signup_payload)
        headers = {"X-Session-Id": register_response.json()["data"]["session_id"]}

        response = api.change_password(
            UserFactory.change_password_payload(
                current_password="ValidPass1",
                new_password="weakpass",
            ),
            headers=headers,
        )

        assert_status_code(response, 400)
