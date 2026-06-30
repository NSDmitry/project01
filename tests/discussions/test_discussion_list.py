from tests.support.assertions import assert_status_code
from tests.support.factories import DiscussionFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestDiscussionList:
    def test_discussions_are_paginated_with_author(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        api.create_discussion(
            DiscussionFactory.create_payload(club_id=club_id, title="Первое"), headers=owner.headers
        )
        api.create_discussion(
            DiscussionFactory.create_payload(club_id=club_id, title="Второе"), headers=owner.headers
        )

        page = api.discussions(club_id, headers=owner.headers, params={"limit": 1, "offset": 0})
        data = page.json()["data"]

        assert_status_code(page, 200)
        assert data["total"] == 2
        assert len(data["items"]) == 1
        # Последние сверху - самое свежее обсуждение первым.
        assert data["items"][0]["title"] == "Второе"
        assert data["items"][0]["author"]["id"] == owner.user_id
