import pytest
from faker import Faker

from tests.support.assertions import assert_status_code
from tests.support.factories import BookclubFactory
from tests.support.flows import AuthFlow, BookclubFlow

faker = Faker()

class TestBookclubsCreate:
    def test_create_bookclub_returns_created_entity(self, api):
        payload = BookclubFactory.payload()
        response = BookclubFlow.create(api, payload=payload)
        data = response.json()["data"]

        assert_status_code(response, 201)
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]

    @pytest.mark.parametrize("name",
                             ["", faker.pystr(min_chars=0, max_chars=2), faker.pystr(min_chars=100, max_chars=200)])
    def test_create_bookclub_validates_name(self, api, name):
        payload = BookclubFactory.payload(
            name=name,
            description=faker.pystr(min_chars=3, max_chars=500),
        )
        assert_status_code(BookclubFlow.create(api, payload=payload), 422)

    @pytest.mark.parametrize("description",
                             ["", faker.pystr(min_chars=0, max_chars=2), faker.pystr(min_chars=501, max_chars=1000)])
    def test_create_bookclub_validates_description(self, api, description):
        payload = BookclubFactory.payload(
            name=faker.pystr(min_chars=3, max_chars=100),
            description=description,
        )
        assert_status_code(BookclubFlow.create(api, payload=payload), 422)

    def test_create_bookclub_assigns_owner(self, api):
        auth = AuthFlow.register(api)
        response = BookclubFlow.create(api, auth=auth)

        assert_status_code(response, 201)
        assert response.json()["data"]["owner"]["id"] == auth.user_id

    def test_create_bookclub_adds_owner_to_members(self, api):
        auth = AuthFlow.register(api)
        response = BookclubFlow.create(api, auth=auth)
        club_id = response.json()["data"]["id"]

        assert_status_code(response, 201)
        assert response.json()["data"]["members_count"] == 1
        members = api.bookclub_members(club_id, headers=auth.headers)
        assert auth.user_id in [member["id"] for member in members.json()["data"]["items"]]

    def test_create_bookclub_rejects_duplicate_name(self, api):
        payload = BookclubFactory.payload(name=faker.pystr(min_chars=4, max_chars=99))
        assert_status_code(BookclubFlow.create(api, payload=payload), 201)

        response = BookclubFlow.create(api, payload=payload)
        assert_status_code(response, 409)
        assert response.json()["message"] == "Клуб с таким названием уже существует"
