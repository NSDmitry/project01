from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow


class TestBookCreate:
    def test_create_with_title_only(self, api):
        auth = AuthFlow.register(api)

        response = api.create_book({"title": "Мастер и Маргарита"}, headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 201)
        assert data["id"] > 0
        assert data["title"] == "Мастер и Маргарита"
        assert data["google_volume_id"] is None
        assert data["author"] is None
        assert data["description"] is None
        assert data["genres"] is None
        assert data["published_year"] is None

    def test_create_with_all_fields(self, api):
        auth = AuthFlow.register(api)

        response = api.create_book(
            {
                "title": "Мастер и Маргарита",
                "author": "Михаил Булгаков",
                "description": "Роман о визите дьявола в Москву",
                "genres": "Классика",
                "published_year": 1967,
            },
            headers=auth.headers,
        )
        data = response.json()["data"]

        assert_status_code(response, 201)
        assert data["author"] == "Михаил Булгаков"
        assert data["description"] == "Роман о визите дьявола в Москву"
        assert data["genres"] == "Классика"
        assert data["published_year"] == 1967
        assert data["google_volume_id"] is None

    def test_create_requires_title(self, api):
        auth = AuthFlow.register(api)

        response = api.create_book({"author": "Михаил Булгаков"}, headers=auth.headers)

        assert_status_code(response, 422)

    def test_create_rejects_empty_title(self, api):
        auth = AuthFlow.register(api)

        response = api.create_book({"title": ""}, headers=auth.headers)

        assert_status_code(response, 422)

    def test_create_requires_auth(self, api):
        response = api.create_book({"title": "Мастер и Маргарита"})

        assert_status_code(response, 401)
