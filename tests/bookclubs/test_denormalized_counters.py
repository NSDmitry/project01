from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestMembersCount:
    """members_count - денормализованный столбец клуба, а не count(*) по club_members.
    Расходится он молча, поэтому проверяем на каждом пути, который меняет состав."""

    def test_owner_counted_on_creation(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        assert api.bookclub(club_id, headers=owner.headers).json()["data"]["members_count"] == 1

    def test_tracks_join_and_leave(self, api):
        owner = AuthFlow.register(api)
        member = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        joined = api.join_bookclub(club_id, headers=member.headers)
        assert_status_code(joined, 200)
        assert joined.json()["data"]["members_count"] == 2

        left = api.leave_bookclub(club_id, headers=member.headers)
        assert_status_code(left, 200)
        assert left.json()["data"]["members_count"] == 1

    def test_duplicate_join_does_not_inflate(self, api):
        owner = AuthFlow.register(api)
        member = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)
        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 409)

        assert api.bookclub(club_id, headers=owner.headers).json()["data"]["members_count"] == 2

    def test_matches_members_page_total(self, api):
        owner = AuthFlow.register(api)
        member = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        api.join_bookclub(club_id, headers=member.headers)

        page = api.bookclub_members(club_id, headers=owner.headers).json()["data"]

        assert page["total"] == 2
        assert len(page["items"]) == 2

    def test_decremented_when_member_deletes_account(self, api):
        owner = AuthFlow.register(api)
        member = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        api.join_bookclub(club_id, headers=member.headers)

        assert_status_code(
            api.delete_current_user(headers=member.headers, payload={"password": "ValidPass1"}), 200
        )

        assert api.bookclub(club_id, headers=owner.headers).json()["data"]["members_count"] == 1


class TestCommentsCount:
    """comments_count треда отдаётся как total страницы комментариев."""

    def test_tracks_create_and_delete(self, api):
        author = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=author).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=author.headers
        ).json()["data"]["id"]

        assert api.comments(thread_id, headers=author.headers).json()["data"]["total"] == 0

        first = api.create_comment(thread_id, CommentFactory.create_payload(), headers=author.headers)
        api.create_comment(thread_id, CommentFactory.create_payload(), headers=author.headers)
        assert api.comments(thread_id, headers=author.headers).json()["data"]["total"] == 2

        comment_id = first.json()["data"]["id"]
        assert_status_code(api.delete_comment(comment_id, headers=author.headers), 200)

        page = api.comments(thread_id, headers=author.headers).json()["data"]
        assert page["total"] == 1
        assert len(page["items"]) == 1

    def test_decremented_when_author_deletes_account(self, api):
        owner = AuthFlow.register(api)
        commenter = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        thread_id = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        ).json()["data"]["id"]
        api.join_bookclub(club_id, headers=commenter.headers)
        api.create_comment(thread_id, CommentFactory.create_payload(), headers=commenter.headers)
        api.create_comment(thread_id, CommentFactory.create_payload(), headers=owner.headers)

        assert_status_code(
            api.delete_current_user(
                headers=commenter.headers,
                params={"delete_comments": "true"},
                payload={"password": "ValidPass1"},
            ),
            200,
        )

        assert api.comments(thread_id, headers=owner.headers).json()["data"]["total"] == 1


class TestOffsetCeiling:
    """Глубокий offset заставляет БД отсортировать и выбросить всё до страницы -
    ручки его не принимают."""

    def test_offset_over_ceiling_rejected(self, api):
        user = AuthFlow.register(api)

        assert_status_code(api.bookclubs(headers=user.headers, offset=10_001), 422)

    def test_offset_at_ceiling_accepted(self, api):
        user = AuthFlow.register(api)

        assert_status_code(api.bookclubs(headers=user.headers, offset=10_000), 200)

    def test_search_offset_over_ceiling_rejected(self, api):
        user = AuthFlow.register(api)

        assert_status_code(
            api.search_bookclubs(headers=user.headers, offset=10_001), 422
        )
