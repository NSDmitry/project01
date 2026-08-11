from tests.support.assertions import assert_status_code
from tests.support.factories import BookclubFactory
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow


def _club_by_request(api, owner):
    return BookclubFlow.create(
        api, auth=owner, payload=BookclubFactory.payload(privacy="by_request")
    ).json()["data"]["id"]


class TestClubJoinRequests:
    def test_applicant_lands_in_queue(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)

        created = api.request_join(club_id, headers=applicant.headers)
        assert_status_code(created, 201)
        assert created.json()["data"]["status"] == "pending"

        queue = api.join_requests(club_id, headers=owner.headers)
        assert_status_code(queue, 200)
        items = queue.json()["data"]["items"]
        assert [item["user"]["id"] for item in items] == [applicant.user_id]

    def test_approve_adds_member(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)
        request_id = api.request_join(club_id, headers=applicant.headers).json()["data"]["id"]

        approved = api.approve_join_request(club_id, request_id, headers=owner.headers)

        assert_status_code(approved, 200)
        assert approved.json()["data"]["status"] == "approved"
        members = api.bookclub_members(club_id, headers=owner.headers)
        assert applicant.user_id in [member["id"] for member in members.json()["data"]["items"]]
        assert api.bookclub(club_id, headers=owner.headers).json()["data"]["members_count"] == 2

    def test_reject_keeps_applicant_outside(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)
        request_id = api.request_join(club_id, headers=applicant.headers).json()["data"]["id"]

        rejected = api.reject_join_request(club_id, request_id, headers=owner.headers)

        assert_status_code(rejected, 200)
        assert rejected.json()["data"]["status"] == "rejected"
        members = api.bookclub_members(club_id, headers=owner.headers)
        assert applicant.user_id not in [member["id"] for member in members.json()["data"]["items"]]

    def test_resolved_request_leaves_queue(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)
        request_id = api.request_join(club_id, headers=applicant.headers).json()["data"]["id"]

        api.reject_join_request(club_id, request_id, headers=owner.headers)

        queue = api.join_requests(club_id, headers=owner.headers).json()["data"]
        assert queue["items"] == []
        assert queue["total"] == 0

    def test_rejected_applicant_can_apply_again(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)
        request_id = api.request_join(club_id, headers=applicant.headers).json()["data"]["id"]
        api.reject_join_request(club_id, request_id, headers=owner.headers)

        repeated = api.request_join(club_id, headers=applicant.headers)

        assert_status_code(repeated, 201)
        assert repeated.json()["data"]["status"] == "pending"
        assert api.join_requests(club_id, headers=owner.headers).json()["data"]["total"] == 1

    def test_reapplied_request_goes_to_the_back_of_the_queue(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        first = AuthFlow.register(api)
        second = AuthFlow.register(api)
        first_id = api.request_join(club_id, headers=first.headers).json()["data"]["id"]
        api.reject_join_request(club_id, first_id, headers=owner.headers)
        api.request_join(club_id, headers=second.headers)

        # Повторная заявка отказника - новая заявка: она должна встать за тем,
        # кто ждёт с прошлого раза, а не вперёд него по старому id.
        reapplied = api.request_join(club_id, headers=first.headers).json()["data"]

        queue = api.join_requests(club_id, headers=owner.headers).json()["data"]["items"]
        assert [item["user"]["id"] for item in queue] == [second.user_id, first.user_id]
        assert reapplied["created_at"] >= queue[0]["created_at"]

    def test_request_resolved_twice_conflicts(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)
        request_id = api.request_join(club_id, headers=applicant.headers).json()["data"]["id"]

        assert_status_code(api.approve_join_request(club_id, request_id, headers=owner.headers), 200)
        assert_status_code(api.reject_join_request(club_id, request_id, headers=owner.headers), 409)

    def test_moderator_resolves_requests(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        moderator = MemberFlow.moderator(api, club_id, owner)
        applicant = AuthFlow.register(api)
        request_id = api.request_join(club_id, headers=applicant.headers).json()["data"]["id"]

        assert_status_code(api.join_requests(club_id, headers=moderator.headers), 200)
        assert_status_code(api.approve_join_request(club_id, request_id, headers=moderator.headers), 200)

    def test_queue_hidden_from_plain_member(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        member = MemberFlow.join_by_invite(api, club_id, owner)

        response = api.join_requests(club_id, headers=member.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "Смотреть заявки может владелец или модератор клуба"

    def test_open_club_does_not_accept_requests(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        applicant = AuthFlow.register(api)

        assert_status_code(api.request_join(club_id, headers=applicant.headers), 409)

    def test_member_cannot_apply(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        member = MemberFlow.join_by_invite(api, club_id, owner)

        assert_status_code(api.request_join(club_id, headers=member.headers), 409)

    def test_request_of_another_club_is_not_found(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        other_club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)
        request_id = api.request_join(club_id, headers=applicant.headers).json()["data"]["id"]

        response = api.approve_join_request(other_club_id, request_id, headers=owner.headers)

        assert_status_code(response, 404)
        assert response.json()["message"] == "Заявка с таким id не найдена"

    def test_requests_of_deleted_user_leave_the_queue(self, api):
        owner = AuthFlow.register(api)
        club_id = _club_by_request(api, owner)
        applicant = AuthFlow.register(api)
        api.request_join(club_id, headers=applicant.headers)

        assert_status_code(
            api.delete_current_user(headers=applicant.headers, payload={"password": "ValidPass1"}), 200
        )

        assert api.join_requests(club_id, headers=owner.headers).json()["data"]["total"] == 0
