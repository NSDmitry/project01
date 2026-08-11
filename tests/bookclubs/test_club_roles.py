from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow, MemberFlow


def _roles(api, club_id, auth):
    items = api.bookclub_members(club_id, headers=auth.headers).json()["data"]["items"]

    return {item["id"]: item["role"] for item in items}


class TestClubRoles:
    def test_owner_role_comes_from_ownership(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        assert _roles(api, club_id, owner) == {owner.user_id: "owner"}

    def test_owner_promotes_member_to_moderator(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        assert_status_code(
            api.set_member_role(club_id, member.user_id, "moderator", headers=owner.headers), 200
        )
        assert _roles(api, club_id, owner)[member.user_id] == "moderator"

    def test_moderator_can_be_demoted(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        moderator = MemberFlow.moderator(api, club_id, owner)

        assert_status_code(
            api.set_member_role(club_id, moderator.user_id, "member", headers=owner.headers), 200
        )
        assert _roles(api, club_id, owner)[moderator.user_id] == "member"

    def test_moderator_cannot_appoint_moderators(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        moderator = MemberFlow.moderator(api, club_id, owner)
        member = MemberFlow.join(api, club_id)

        response = api.set_member_role(club_id, member.user_id, "moderator", headers=moderator.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "Назначать роли может только владелец клуба"

    def test_owner_role_is_not_assignable(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        assert_status_code(
            api.set_member_role(club_id, member.user_id, "owner", headers=owner.headers), 422
        )

    def test_owner_own_role_is_not_editable(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]

        response = api.set_member_role(club_id, owner.user_id, "member", headers=owner.headers)

        assert_status_code(response, 422)
        assert response.json()["message"] == "Роль владельца меняется передачей клуба"

    def test_role_of_outsider_is_not_found(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        outsider = AuthFlow.register(api)

        assert_status_code(
            api.set_member_role(club_id, outsider.user_id, "moderator", headers=owner.headers), 404
        )


class TestClubMemberRemoval:
    def test_owner_removes_member(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        response = api.remove_member(club_id, member.user_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["members_count"] == 1
        assert member.user_id not in _roles(api, club_id, owner)

    def test_moderator_removes_plain_member(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        moderator = MemberFlow.moderator(api, club_id, owner)
        member = MemberFlow.join(api, club_id)

        assert_status_code(api.remove_member(club_id, member.user_id, headers=moderator.headers), 200)

    def test_moderator_cannot_remove_moderator(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        first = MemberFlow.moderator(api, club_id, owner)
        second = MemberFlow.moderator(api, club_id, owner)

        response = api.remove_member(club_id, second.user_id, headers=first.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "Модератор не может исключить другого модератора"

    def test_owner_cannot_be_removed(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        moderator = MemberFlow.moderator(api, club_id, owner)

        response = api.remove_member(club_id, owner.user_id, headers=moderator.headers)

        assert_status_code(response, 403)
        assert response.json()["message"] == "Владелец не может покинуть клуб - сначала передайте клуб"

    def test_owner_leaves_only_after_transfer(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        assert_status_code(api.leave_bookclub(club_id, headers=owner.headers), 403)

        api.transfer_bookclub(club_id, member.user_id, headers=owner.headers)
        assert_status_code(api.leave_bookclub(club_id, headers=owner.headers), 200)

    def test_plain_member_cannot_remove_anyone(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        other = MemberFlow.join(api, club_id)

        assert_status_code(api.remove_member(club_id, other.user_id, headers=member.headers), 403)

    def test_removing_outsider_conflicts(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        outsider = AuthFlow.register(api)

        assert_status_code(api.remove_member(club_id, outsider.user_id, headers=owner.headers), 409)

    def test_removed_member_can_join_again(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        api.remove_member(club_id, member.user_id, headers=owner.headers)

        assert_status_code(api.join_bookclub(club_id, headers=member.headers), 200)


class TestClubOwnershipTransfer:
    def test_owner_transfers_club_to_member(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)

        response = api.transfer_bookclub(club_id, member.user_id, headers=owner.headers)

        assert_status_code(response, 200)
        assert response.json()["data"]["owner"]["id"] == member.user_id
        assert _roles(api, club_id, member) == {owner.user_id: "member", member.user_id: "owner"}

    def test_new_owner_controls_the_club(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        member = MemberFlow.join(api, club_id)
        api.transfer_bookclub(club_id, member.user_id, headers=owner.headers)

        assert_status_code(api.delete_bookclub(club_id, headers=owner.headers), 403)
        assert_status_code(api.delete_bookclub(club_id, headers=member.headers), 200)

    def test_moderator_loses_role_when_becoming_owner(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        moderator = MemberFlow.moderator(api, club_id, owner)

        api.transfer_bookclub(club_id, moderator.user_id, headers=owner.headers)

        assert _roles(api, club_id, moderator)[moderator.user_id] == "owner"

    def test_transfer_to_outsider_is_rejected(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        outsider = AuthFlow.register(api)

        response = api.transfer_bookclub(club_id, outsider.user_id, headers=owner.headers)

        assert_status_code(response, 422)
        assert response.json()["message"] == "Передать клуб можно только его участнику"

    def test_only_owner_transfers_the_club(self, api):
        owner = AuthFlow.register(api)
        club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
        moderator = MemberFlow.moderator(api, club_id, owner)

        assert_status_code(
            api.transfer_bookclub(club_id, moderator.user_id, headers=moderator.headers), 403
        )
