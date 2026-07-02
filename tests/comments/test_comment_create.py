from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestCommentCreate:
    def test_member_can_create_comment(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        response = api.create_comment(
            thread_id, CommentFactory.create_payload(content="Комментарий"), headers=owner.headers
        )

        assert_status_code(response, 201)
        data = response.json()["data"]
        assert data["content"] == "Комментарий"
        assert data["thread_id"] == thread_id
        assert data["author"]["id"] == owner.user_id

    def test_outsider_cannot_create_comment(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        outsider = AuthFlow.register(api)
        response = api.create_comment(
            thread_id, CommentFactory.create_payload(), headers=outsider.headers
        )

        assert_status_code(response, 403)

    def test_create_comment_requires_authorization(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        response = api.create_comment(thread_id, CommentFactory.create_payload(), headers={})

        assert_status_code(response, 401)

    def test_create_comment_requires_existing_thread(self, api):
        auth = AuthFlow.register(api)

        response = api.create_comment(999999, CommentFactory.create_payload(), headers=auth.headers)

        assert_status_code(response, 404)
