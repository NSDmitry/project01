import httpx

from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow


class TestGoogleUnavailable:
    def test_search_returns_503_when_google_rate_limits(self, api, monkeypatch):
        # Реальный GoogleBooksClient, но httpx.AsyncClient.get отдаёт 429 без сети.
        # TestClient ходит через синхронный httpx.Client - его патч не задевает.
        async def fake_get(self, url, **kwargs):
            return httpx.Response(429, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
        auth = AuthFlow.register(api)

        response = api.search_books("мастер", headers=auth.headers)
        body = response.json()

        assert_status_code(response, 503)
        assert body["success"] is False
        assert body["message"] == "Сервис поиска книг временно недоступен"

    def test_search_returns_503_on_timeout(self, api, monkeypatch):
        async def fake_get(self, url, **kwargs):
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
        auth = AuthFlow.register(api)

        response = api.search_books("мастер", headers=auth.headers)
        body = response.json()

        assert_status_code(response, 503)
        assert body["success"] is False
        assert body["message"] == "Сервис поиска книг временно недоступен"
