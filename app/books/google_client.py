from typing import Any, List, Optional

import httpx

from app.books.schemas import BookSuggestionResponse
from app.core.errors.errors import ServiceUnavailable

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
UNAVAILABLE_MESSAGE = "Сервис поиска книг временно недоступен"


class GoogleBooksClient:
    api_key: str

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def _params(self, **params: Any) -> dict[str, Any]:
        if self.api_key:
            params["key"] = self.api_key
        return params

    @staticmethod
    def _cover_url(info: dict) -> Optional[str]:
        links = info.get("imageLinks", {})
        url = links.get("thumbnail") or links.get("smallThumbnail")
        # Google отдаёт ссылки по http, клиенты с ATS/CSP такую картинку не покажут.
        return url.replace("http://", "https://", 1) if url else None

    @classmethod
    def _parse(cls, item: dict) -> BookSuggestionResponse:
        info = item.get("volumeInfo", {})
        published_date = info.get("publishedDate", "")
        year = int(published_date[:4]) if published_date[:4].isdigit() else None

        return BookSuggestionResponse(
            volume_id=item["id"],
            title=info.get("title", ""),
            author=", ".join(info.get("authors", [])) or None,
            description=info.get("description") or None,
            genres=", ".join(info.get("categories", [])) or None,
            published_year=year,
            cover_url=cls._cover_url(info),
            # Google отдаёт 0 для книг без известного объёма.
            page_count=info.get("pageCount") or None,
        )

    async def _get(self, url: str, **params: Any) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                return await client.get(url, params=self._params(**params))
        except httpx.HTTPError:
            raise ServiceUnavailable(UNAVAILABLE_MESSAGE)

    async def search(self, query: str, limit: int = 10) -> List[BookSuggestionResponse]:
        response = await self._get(GOOGLE_BOOKS_URL, q=query, maxResults=limit, printType="books")
        if response.is_error:
            raise ServiceUnavailable(UNAVAILABLE_MESSAGE)

        items = response.json().get("items", [])
        return [self._parse(item) for item in items if item.get("volumeInfo", {}).get("title")]

    async def get_volume(self, volume_id: str) -> Optional[BookSuggestionResponse]:
        response = await self._get(f"{GOOGLE_BOOKS_URL}/{volume_id}")

        # Google отвечает 404 на несуществующий и 400/503 на некорректный volume_id.
        if response.status_code in (400, 404, 503):
            return None
        if response.is_error:
            raise ServiceUnavailable(UNAVAILABLE_MESSAGE)

        return self._parse(response.json())
