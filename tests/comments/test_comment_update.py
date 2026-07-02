from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _create_comment(api, auth, thread_id):
    return api.create_comment(thread_id, CommentFactory.create_payload(), headers=auth.headers)


class TestCommentUpdate:
    def test_author_can_update_own_comment(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        comment_id = _create_comment(api, member, thread_id).json()["data"]["id"]

        response = api.update_comment(
            comment_id, CommentFactory.update_payload(content="Обновлено"), headers=member.headers
        )

        assert_status_code(response, 200)
        assert response.json()["data"]["content"] == "Обновлено"

    def test_club_owner_cannot_update_member_comment(self, api):
        # В отличие от тредов, где владелец клуба может править чужой тред,
        # комментарий редактирует только его автор.
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        comment_id = _create_comment(api, member, thread_id).json()["data"]["id"]

        response = api.update_comment(
            comment_id, CommentFactory.update_payload(), headers=owner.headers
        )

        assert_status_code(response, 403)

    def test_outsider_cannot_update_comment(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        comment_id = _create_comment(api, member, thread_id).json()["data"]["id"]

        outsider = AuthFlow.register(api)
        response = api.update_comment(
            comment_id, CommentFactory.update_payload(), headers=outsider.headers
        )

        assert_status_code(response, 403)
