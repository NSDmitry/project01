from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _create_comment(api, auth, thread_id):
    return api.create_comment(thread_id, CommentFactory.create_payload(), headers=auth.headers)


class TestCommentDelete:
    def test_author_can_delete_own_comment(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        comment_id = _create_comment(api, member, thread_id).json()["data"]["id"]

        response = api.delete_comment(comment_id, headers=member.headers)

        assert_status_code(response, 200)

    def test_club_owner_can_delete_member_comment(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        comment_id = _create_comment(api, member, thread_id).json()["data"]["id"]

        response = api.delete_comment(comment_id, headers=owner.headers)

        assert_status_code(response, 200)

    def test_outsider_cannot_delete_comment(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        comment_id = _create_comment(api, member, thread_id).json()["data"]["id"]

        outsider = AuthFlow.register(api)
        response = api.delete_comment(comment_id, headers=outsider.headers)

        assert_status_code(response, 403)

    def test_delete_comment_returns_not_found_for_unknown_id(self, api):
        auth = AuthFlow.register(api)

        response = api.delete_comment(999999, headers=auth.headers)

        assert_status_code(response, 404)
