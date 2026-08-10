import pytest
from faker import Faker

from tests.support.assertions import assert_status_code
from tests.support.factories import BookclubFactory
from tests.support.flows import AuthFlow, BookclubFlow

faker = Faker()


class TestBookclubsUpdate:
    def test_update_replaces_name_and_description(self, api):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        response = api.update_bookclub(
            club["id"],
            {"name": "Новое название", "description": "Новое описание"},
            headers=auth.headers,
        )

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["name"] == "Новое название"
        assert data["description"] == "Новое описание"

    def test_update_persists(self, api):
        # Ответ ручки может быть правильным, а в БД ничего не уехать -
        # проверяем отдельным запросом, а не только телом ответа.
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        api.update_bookclub(
            club["id"],
            {"name": "Сохранённое название", "description": "Сохранённое описание"},
            headers=auth.headers,
        )
        fresh = api.bookclub(club["id"], headers=auth.headers).json()["data"]

        assert fresh["name"] == "Сохранённое название"
        assert fresh["description"] == "Сохранённое описание"

    def test_update_name_only_keeps_description(self, api):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        response = api.update_bookclub(club["id"], {"name": "Только название"}, headers=auth.headers)

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["name"] == "Только название"
        assert data["description"] == club["description"]

    def test_update_description_only_keeps_name(self, api):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        response = api.update_bookclub(club["id"], {"description": "Только описание"}, headers=auth.headers)

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["name"] == club["name"]
        assert data["description"] == "Только описание"

    def test_update_empty_payload_changes_nothing(self, api):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        response = api.update_bookclub(club["id"], {}, headers=auth.headers)

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["name"] == club["name"]
        assert data["description"] == club["description"]

    def test_update_keeps_genres_owner_and_members(self, api):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(
            api, auth=auth, payload=BookclubFactory.payload(genres=["sci-fi", "fantasy"])
        ).json()["data"]

        data = api.update_bookclub(
            club["id"],
            {"name": "Название после правки", "description": "Описание после правки"},
            headers=auth.headers,
        ).json()["data"]

        assert {genre["code"] for genre in data["genres"]} == {"sci-fi", "fantasy"}
        assert data["owner"]["id"] == auth.user_id
        assert data["members_count"] == 1

    @pytest.mark.parametrize("name",
                             ["", faker.pystr(min_chars=0, max_chars=2), faker.pystr(min_chars=101, max_chars=200)])
    def test_update_validates_name(self, api, name):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        assert_status_code(api.update_bookclub(club["id"], {"name": name}, headers=auth.headers), 422)

    @pytest.mark.parametrize("description",
                             ["", faker.pystr(min_chars=0, max_chars=2), faker.pystr(min_chars=501, max_chars=1000)])
    def test_update_validates_description(self, api, description):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        assert_status_code(
            api.update_bookclub(club["id"], {"description": description}, headers=auth.headers), 422
        )

    def test_update_rejects_duplicate_name(self, api):
        auth = AuthFlow.register(api)
        taken = BookclubFlow.create(
            api, auth=auth, payload=BookclubFactory.payload(name="Занятое название")
        ).json()["data"]
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        response = api.update_bookclub(club["id"], {"name": taken["name"]}, headers=auth.headers)

        assert_status_code(response, 409)

    def test_update_keeps_own_name_unchanged(self, api):
        # Уникальность не должна ловить сам обновляемый клуб на его же имени.
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]

        response = api.update_bookclub(
            club["id"], {"name": club["name"], "description": "Другое описание"}, headers=auth.headers
        )

        assert_status_code(response, 200)
        assert response.json()["data"]["description"] == "Другое описание"

    def test_update_rejected_for_non_owner(self, api):
        owner = AuthFlow.register(api)
        stranger = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=owner).json()["data"]

        response = api.update_bookclub(
            club["id"], {"name": "Чужое название"}, headers=stranger.headers
        )

        assert_status_code(response, 403)
        fresh = api.bookclub(club["id"], headers=owner.headers).json()["data"]
        assert fresh["name"] == club["name"]

    def test_update_requires_auth(self, api):
        owner = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=owner).json()["data"]

        assert_status_code(api.update_bookclub(club["id"], {"name": "Без авторизации"}), 401)

    def test_update_missing_club_returns_404(self, api):
        auth = AuthFlow.register(api)

        assert_status_code(api.update_bookclub(999999, {"name": "Нет клуба"}, headers=auth.headers), 404)
