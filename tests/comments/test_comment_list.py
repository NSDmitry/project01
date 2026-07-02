from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestCommentList:
    def test_comments_are_paginated_oldest_first_with_author(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        api.create_comment(
            thread_id, CommentFactory.create_payload(content="Первый"), headers=owner.headers
        )
        api.create_comment(
            thread_id, CommentFactory.create_payload(content="Второй"), headers=owner.headers
        )

        page = api.comments(thread_id, headers=owner.headers, params={"limit": 1, "offset": 0})
        data = page.json()["data"]

        assert_status_code(page, 200)
        assert data["total"] == 2
        assert len(data["items"]) == 1
        # Старые сверху - самый ранний комментарий первым.
        assert data["items"][0]["content"] == "Первый"
        assert data["items"][0]["author"]["id"] == owner.user_id

    def test_comments_require_existing_thread(self, api):
        auth = AuthFlow.register(api)

        response = api.comments(999999, headers=auth.headers)

        assert_status_code(response, 404)
