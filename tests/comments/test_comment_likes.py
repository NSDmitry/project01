from datetime import timedelta

from app.iam.models import UserSession
from tests.support.assertions import assert_status_code
from tests.support.factories import CommentFactory, ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _create_comment(api, auth):
    club_id = BookclubFlow.create(api, auth=auth).json()["data"]["id"]
    thread_id = api.create_thread(
        ThreadFactory.create_payload(club_id=club_id), headers=auth.headers
    ).json()["data"]["id"]
    comment_id = api.create_comment(
        thread_id, CommentFactory.create_payload(), headers=auth.headers
    ).json()["data"]["id"]
    return club_id, thread_id, comment_id


class TestCommentLikes:
    def test_member_can_like_comment(self, api):
        owner = AuthFlow.register(api)
        _, _, comment_id = _create_comment(api, owner)

        response = api.like_comment(comment_id, headers=owner.headers)

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["likes_count"] == 1
        assert data["is_liked"] is True

    def test_like_is_idempotent(self, api):
        owner = AuthFlow.register(api)
        _, _, comment_id = _create_comment(api, owner)

        api.like_comment(comment_id, headers=owner.headers)
        response = api.like_comment(comment_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["likes_count"] == 1

    def test_unlike_removes_like(self, api):
        owner = AuthFlow.register(api)
        _, _, comment_id = _create_comment(api, owner)
        api.like_comment(comment_id, headers=owner.headers)

        response = api.unlike_comment(comment_id, headers=owner.headers)

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["likes_count"] == 0
        assert data["is_liked"] is False

    def test_unlike_without_like_is_idempotent(self, api):
        owner = AuthFlow.register(api)
        _, _, comment_id = _create_comment(api, owner)

        response = api.unlike_comment(comment_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["likes_count"] == 0

    def test_comment_list_shows_likes_for_current_user(self, api):
        owner = AuthFlow.register(api)
        club_id, thread_id, comment_id = _create_comment(api, owner)

        member = AuthFlow.register(api)
        api.join_bookclub(club_id, headers=member.headers)
        api.like_comment(comment_id, headers=owner.headers)
        api.like_comment(comment_id, headers=member.headers)

        comment = api.comments(thread_id, headers=member.headers).json()["data"]["items"][0]
        assert comment["likes_count"] == 2
        assert comment["is_liked"] is True

        api.unlike_comment(comment_id, headers=member.headers)
        comment = api.comments(thread_id, headers=member.headers).json()["data"]["items"][0]
        assert comment["likes_count"] == 1
        assert comment["is_liked"] is False

    def test_comment_list_with_expired_session_is_anonymous(self, api, db):
        owner = AuthFlow.register(api)
        _, thread_id, comment_id = _create_comment(api, owner)
        api.like_comment(comment_id, headers=owner.headers)

        db.expire_all()
        session = db.query(UserSession).filter(UserSession.user_id == owner.user_id).first()
        session.last_used = session.last_used - timedelta(days=31)
        db.commit()

        response = api.comments(thread_id, headers=owner.headers)

        assert_status_code(response, 200)
        comment = response.json()["data"]["items"][0]
        assert comment["likes_count"] == 1
        assert comment["is_liked"] is False

    def test_comment_list_without_auth_shows_likes_count(self, api):
        owner = AuthFlow.register(api)
        _, thread_id, comment_id = _create_comment(api, owner)
        api.like_comment(comment_id, headers=owner.headers)

        comment = api.comments(thread_id).json()["data"]["items"][0]
        assert comment["likes_count"] == 1
        assert comment["is_liked"] is False

    def test_likers_list_returns_users_freshest_first(self, api):
        owner = AuthFlow.register(api)
        club_id, _, comment_id = _create_comment(api, owner)

        member = AuthFlow.register(api)
        api.join_bookclub(club_id, headers=member.headers)
        api.like_comment(comment_id, headers=owner.headers)
        api.like_comment(comment_id, headers=member.headers)

        response = api.comment_likers(comment_id)

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["total"] == 2
        assert [item["id"] for item in data["items"]] == [member.user_id, owner.user_id]

    def test_likers_list_is_paginated(self, api):
        owner = AuthFlow.register(api)
        club_id, _, comment_id = _create_comment(api, owner)

        member = AuthFlow.register(api)
        api.join_bookclub(club_id, headers=member.headers)
        api.like_comment(comment_id, headers=owner.headers)
        api.like_comment(comment_id, headers=member.headers)

        first = api.comment_likers(comment_id, params={"limit": 1, "offset": 0}).json()["data"]
        second = api.comment_likers(comment_id, params={"limit": 1, "offset": 1}).json()["data"]

        assert first["total"] == 2
        assert [item["id"] for item in first["items"]] == [member.user_id]
        assert [item["id"] for item in second["items"]] == [owner.user_id]

    def test_likers_list_returns_not_found_for_unknown_comment(self, api):
        response = api.comment_likers(999999)

        assert_status_code(response, 404)

    def test_outsider_cannot_like_comment(self, api):
        owner = AuthFlow.register(api)
        _, _, comment_id = _create_comment(api, owner)

        outsider = AuthFlow.register(api)
        response = api.like_comment(comment_id, headers=outsider.headers)

        assert_status_code(response, 403)

    def test_like_requires_authorization(self, api):
        owner = AuthFlow.register(api)
        _, _, comment_id = _create_comment(api, owner)

        response = api.like_comment(comment_id, headers={})

        assert_status_code(response, 401)

    def test_like_returns_not_found_for_unknown_comment(self, api):
        auth = AuthFlow.register(api)

        response = api.like_comment(999999, headers=auth.headers)

        assert_status_code(response, 404)
