from sqlalchemy import text

from tests.support.assertions import assert_status_code
from tests.support.factories import GenreFactory
from tests.support.flows import AuthFlow


def _admin(api, db):
    auth = AuthFlow.register(api)
    db.execute(text("UPDATE users SET is_admin = true WHERE id = :id"), {"id": auth.user_id})
    db.commit()
    return auth


class TestGenreCodeValidation:
    def test_create_genre_rejects_cyrillic_code(self, api, db):
        auth = _admin(api, db)

        response = api.create_genre(GenreFactory.payload(code="жанр"), headers=auth.headers)

        assert_status_code(response, 422)

    def test_create_genre_rejects_code_with_space(self, api, db):
        auth = _admin(api, db)

        response = api.create_genre(GenreFactory.payload(code="my genre"), headers=auth.headers)

        assert_status_code(response, 422)
