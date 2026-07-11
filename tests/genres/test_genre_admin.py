import pytest
from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import GenreFactory
from tests.support.flows import AuthFlow


def _promote_to_admin(db, auth):
    db.execute(text("UPDATE users SET is_admin = true WHERE id = :id"), {"id": auth.user_id})
    db.commit()


@pytest.fixture
def admin(api, db):
    """Admin session that deletes every genre it created, once the test ends.

    genres не чистится между тестами (это каталог, см. conftest.clear_db) -
    без явной очистки жанры, созданные в тестах, накапливались бы и ломали
    тесты, завязанные на точный размер каталога.
    """
    auth = AuthFlow.register(api)
    _promote_to_admin(db, auth)
    created_ids = []

    yield auth, created_ids

    for genre_id in created_ids:
        api.delete_genre(genre_id, headers=auth.headers)


class TestGenreCatalog:
    def test_catalog_returns_seeded_genres(self, api):
        auth = AuthFlow.register(api)
        response = api.genres(headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        codes = [genre["code"] for genre in data]
        assert "fiction" in codes

    def test_catalog_requires_auth(self, api):
        assert_status_code(api.genres(), 401)


class TestGenreCreate:
    def test_admin_can_create_genre(self, api, admin):
        auth, created_ids = admin

        payload = GenreFactory.payload()
        response = api.create_genre(payload, headers=auth.headers)
        data = response.json()["data"]
        created_ids.append(data["id"])

        assert_status_code(response, 201)
        assert data["code"] == payload["code"]
        assert data["name"] == payload["name"]

        catalog = api.genres(headers=auth.headers).json()["data"]
        assert payload["code"] in [genre["code"] for genre in catalog]

    def test_create_genre_requires_admin(self, api):
        auth = AuthFlow.register(api)
        response = api.create_genre(GenreFactory.payload(), headers=auth.headers)
        assert_status_code(response, 403)

    def test_create_genre_requires_auth(self, api):
        assert_status_code(api.create_genre(GenreFactory.payload()), 401)

    def test_create_genre_rejects_duplicate_code(self, api, admin):
        auth, created_ids = admin

        payload = GenreFactory.payload()
        first = api.create_genre(payload, headers=auth.headers)
        assert_status_code(first, 201)
        created_ids.append(first.json()["data"]["id"])

        response = api.create_genre(payload, headers=auth.headers)
        assert_status_code(response, 409)

    def test_create_genre_validates_empty_code(self, api, admin):
        auth, _ = admin

        response = api.create_genre(GenreFactory.payload(code=""), headers=auth.headers)
        assert_status_code(response, 422)


class TestGenreUpdate:
    def test_admin_can_update_genre(self, api, admin):
        auth, created_ids = admin
        genre_id = api.create_genre(GenreFactory.payload(), headers=auth.headers).json()["data"]["id"]
        created_ids.append(genre_id)

        new_payload = GenreFactory.payload()
        response = api.update_genre(genre_id, new_payload, headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        assert data["code"] == new_payload["code"]
        assert data["name"] == new_payload["name"]

    def test_update_genre_requires_admin(self, api, admin):
        auth, created_ids = admin
        genre_id = api.create_genre(GenreFactory.payload(), headers=auth.headers).json()["data"]["id"]
        created_ids.append(genre_id)

        outsider = AuthFlow.register(api)
        response = api.update_genre(genre_id, GenreFactory.payload(), headers=outsider.headers)
        assert_status_code(response, 403)

    def test_update_unknown_genre_returns_404(self, api, admin):
        auth, _ = admin

        response = api.update_genre(999999, GenreFactory.payload(), headers=auth.headers)
        assert_status_code(response, 404)

    def test_update_genre_rejects_duplicate_code(self, api, admin):
        auth, created_ids = admin
        first = api.create_genre(GenreFactory.payload(), headers=auth.headers).json()["data"]
        second_id = api.create_genre(GenreFactory.payload(), headers=auth.headers).json()["data"]["id"]
        created_ids.extend([first["id"], second_id])

        response = api.update_genre(
            second_id, GenreFactory.payload(code=first["code"]), headers=auth.headers
        )
        assert_status_code(response, 409)


class TestGenreDelete:
    def test_admin_can_delete_genre(self, api, admin):
        auth, _ = admin
        genre_id = api.create_genre(GenreFactory.payload(), headers=auth.headers).json()["data"]["id"]

        response = api.delete_genre(genre_id, headers=auth.headers)
        assert_status_code(response, 200)

        response = api.update_genre(genre_id, GenreFactory.payload(), headers=auth.headers)
        assert_status_code(response, 404)

    def test_delete_genre_requires_admin(self, api, admin):
        auth, created_ids = admin
        genre_id = api.create_genre(GenreFactory.payload(), headers=auth.headers).json()["data"]["id"]
        created_ids.append(genre_id)

        outsider = AuthFlow.register(api)
        response = api.delete_genre(genre_id, headers=outsider.headers)
        assert_status_code(response, 403)

    def test_delete_unknown_genre_returns_404(self, api, admin):
        auth, _ = admin

        response = api.delete_genre(999999, headers=auth.headers)
        assert_status_code(response, 404)

    def test_delete_genre_requires_auth(self, api):
        assert_status_code(api.delete_genre(1), 401)
