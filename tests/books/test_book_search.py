from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow
from tests.support.google_books import install_fake_google, suggestion


class TestBookSearch:
    def test_search_returns_suggestions(self, api):
        install_fake_google([suggestion(volume_id="vol-1")])
        auth = AuthFlow.register(api)

        response = api.search_books("мастер", headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        assert len(data) == 1
        assert data[0]["volume_id"] == "vol-1"
        assert data[0]["title"] == "Мастер и Маргарита"
        assert data[0]["author"] == "Михаил Булгаков"
        assert data[0]["published_year"] == 1967

    def test_search_requires_auth(self, api):
        install_fake_google([suggestion()])

        response = api.search_books("мастер")

        assert_status_code(response, 401)

    def test_search_requires_query(self, api):
        install_fake_google([])
        auth = AuthFlow.register(api)

        response = api.search_books("", headers=auth.headers)

        assert_status_code(response, 422)
