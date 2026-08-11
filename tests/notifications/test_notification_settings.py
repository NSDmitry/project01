from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow


class TestNotificationSettings:
    def test_defaults_all_enabled(self, api):
        auth = AuthFlow.register(api)

        response = api.notification_settings(headers=auth.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["disabled"] == []

    def test_put_replaces_disabled_set(self, api):
        auth = AuthFlow.register(api)

        response = api.update_notification_settings(
            {"disabled": ["comment_in_thread", "reading_started"]}, headers=auth.headers
        )

        assert_status_code(response, 200)
        assert sorted(response.json()["data"]["disabled"]) == ["comment_in_thread", "reading_started"]

        # Replace-set: новый PUT полностью заменяет прежний список.
        response = api.update_notification_settings({"disabled": []}, headers=auth.headers)

        assert_status_code(response, 200)
        assert api.notification_settings(headers=auth.headers).json()["data"]["disabled"] == []

    def test_put_deduplicates(self, api):
        auth = AuthFlow.register(api)

        response = api.update_notification_settings(
            {"disabled": ["stage_deadline", "stage_deadline"]}, headers=auth.headers
        )

        assert response.json()["data"]["disabled"] == ["stage_deadline"]

    def test_put_rejects_unknown_type(self, api):
        auth = AuthFlow.register(api)

        response = api.update_notification_settings({"disabled": ["carrier_pigeon"]}, headers=auth.headers)

        assert_status_code(response, 422)

    def test_requires_authorization(self, api):
        assert_status_code(api.notification_settings(headers={}), 401)
        assert_status_code(api.update_notification_settings({"disabled": []}, headers={}), 401)
