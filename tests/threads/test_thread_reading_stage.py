from tests.support.assertions import assert_status_code
from tests.support.factories import ThreadFactory
from tests.support.flows import AuthFlow, BookclubFlow, ReadingFlow


def _club_with_stages(api):
    owner = AuthFlow.register(api)
    club_id = BookclubFlow.create(api, auth=owner).json()["data"]["id"]
    stages = ReadingFlow.create(api, club_id, owner).json()["data"]["stages"]

    return owner, club_id, stages


class TestThreadReadingStage:
    def test_thread_can_be_attached_to_stage(self, api):
        owner, club_id, stages = _club_with_stages(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, reading_stage_id=stages[0]["id"]),
            headers=owner.headers,
        )

        assert_status_code(response, 201)
        assert response.json()["data"]["reading_stage_id"] == stages[0]["id"]

    def test_thread_without_stage_keeps_it_empty(self, api):
        owner, club_id, _ = _club_with_stages(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id), headers=owner.headers
        )

        assert_status_code(response, 201)
        assert response.json()["data"]["reading_stage_id"] is None

    def test_stage_of_another_club_is_rejected(self, api):
        owner, club_id, _ = _club_with_stages(api)
        other_owner, _, other_stages = _club_with_stages(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, reading_stage_id=other_stages[0]["id"]),
            headers=owner.headers,
        )

        assert_status_code(response, 404)

    def test_unknown_stage_is_rejected(self, api):
        owner, club_id, _ = _club_with_stages(api)

        response = api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, reading_stage_id=999999),
            headers=owner.headers,
        )

        assert_status_code(response, 404)

    def test_threads_are_filtered_by_stage(self, api):
        owner, club_id, stages = _club_with_stages(api)
        api.create_thread(
            ThreadFactory.create_payload(
                club_id=club_id, title="Про первые главы", reading_stage_id=stages[0]["id"]
            ),
            headers=owner.headers,
        )
        api.create_thread(
            ThreadFactory.create_payload(
                club_id=club_id, title="Про финал", reading_stage_id=stages[1]["id"]
            ),
            headers=owner.headers,
        )
        api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, title="Про книгу целиком"),
            headers=owner.headers,
        )

        response = api.threads(club_id, params={"reading_stage_id": stages[0]["id"]})
        page = response.json()["data"]

        assert_status_code(response, 200)
        assert [item["title"] for item in page["items"]] == ["Про первые главы"]
        # С фильтром общее число берётся запросом, а не из счётчика клуба.
        assert page["total"] == 1

    def test_threads_without_filter_return_all(self, api):
        owner, club_id, stages = _club_with_stages(api)
        api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, reading_stage_id=stages[0]["id"]),
            headers=owner.headers,
        )
        api.create_thread(ThreadFactory.create_payload(club_id=club_id), headers=owner.headers)

        response = api.threads(club_id)

        assert_status_code(response, 200)
        assert response.json()["data"]["total"] == 2

    def test_deleting_club_removes_threads_with_stages(self, api):
        owner, club_id, stages = _club_with_stages(api)
        api.create_thread(
            ThreadFactory.create_payload(club_id=club_id, reading_stage_id=stages[0]["id"]),
            headers=owner.headers,
        )

        response = api.delete_bookclub(club_id, headers=owner.headers)

        assert_status_code(response, 200)
