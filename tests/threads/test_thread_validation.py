from tests.support.assertions import assert_status_code
from tests.support.factories import ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _club(api):
    auth = AuthFlow.register(api)
    club_id = BookclubFlow.create(api, auth=auth).json()["data"]["id"]
    return auth, club_id


class TestThreadValidation:
    def test_create_thread_rejects_empty_title(self, api):
        auth, club_id = _club(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title=""), headers=auth.headers
        )

        assert_status_code(response, 422)

    def test_create_thread_rejects_whitespace_title(self, api):
        auth, club_id = _club(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title="   "), headers=auth.headers
        )

        assert_status_code(response, 422)

    def test_create_thread_rejects_empty_content(self, api):
        auth, club_id = _club(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, content=""), headers=auth.headers
        )

        assert_status_code(response, 422)

    def test_create_thread_trims_title(self, api):
        auth, club_id = _club(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title="  Заголовок  "),
            headers=auth.headers,
        )

        assert_status_code(response, 201)
        assert response.json()["data"]["title"] == "Заголовок"
