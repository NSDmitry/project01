from tests.support.assertions import assert_status_code
from tests.support.factories import DiscussionFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _create_discussion(api, auth, club_id):
    return api.create_discussion(
        DiscussionFactory.create_payload(club_id=club_id),
        headers=auth.headers,
    )


class TestDiscussionUpdate:
    def test_author_can_update_own_discussion(self, api):
        # Регрессия: автор-не-владелец должен иметь возможность править своё обсуждение.
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        discussion_id = _create_discussion(api, member, club_id).json()["data"]["id"]

        response = api.update_discussion(
            discussion_id, DiscussionFactory.update_payload(title="Обновлено"), headers=member.headers
        )

        assert_status_code(response, 200)
        assert response.json()["data"]["title"] == "Обновлено"

    def test_club_owner_can_update_member_discussion(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        discussion_id = _create_discussion(api, member, club_id).json()["data"]["id"]

        response = api.update_discussion(
            discussion_id, DiscussionFactory.update_payload(title="Правка владельца"), headers=owner.headers
        )

        assert_status_code(response, 200)
        assert response.json()["data"]["title"] == "Правка владельца"

    def test_outsider_cannot_update_discussion(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        member = AuthFlow.register(api)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        discussion_id = _create_discussion(api, member, club_id).json()["data"]["id"]

        outsider = AuthFlow.register(api)
        response = api.update_discussion(
            discussion_id, DiscussionFactory.update_payload(), headers=outsider.headers
        )

        assert_status_code(response, 409)
