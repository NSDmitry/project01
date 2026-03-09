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
