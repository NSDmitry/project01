from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _thread(api):
    auth = AuthFlow.register(api)
    club_id = BookclubFlow.create(api, auth=auth).json()["data"]["id"]
    thread_id = api.create_thread(
        ThreadFactory.create_payload(club_id=club_id), headers=auth.headers
    ).json()["data"]["id"]
    return auth, thread_id


class TestCommentValidation:
    def test_create_comment_rejects_empty_content(self, api):
        auth, thread_id = _thread(api)

        response = api.create_comment(
            thread_id, CommentFactory.create_payload(content=""), headers=auth.headers
        )

        assert_status_code(response, 422)

    def test_create_comment_rejects_whitespace_content(self, api):
        auth, thread_id = _thread(api)

        response = api.create_comment(
            thread_id, CommentFactory.create_payload(content="   "), headers=auth.headers
        )

        assert_status_code(response, 422)
