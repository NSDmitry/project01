from typing import List, Optional

import httpx

from app.books.schemas import BookSuggestionResponse

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksClient:
    api_key: str

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def _params(self, **params) -> dict:
        if self.api_key:
            params["key"] = self.api_key
        return params

    @staticmethod
    def _parse(item: dict) -> BookSuggestionResponse:
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
        )

    async def search(self, query: str, limit: int = 10) -> List[BookSuggestionResponse]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                GOOGLE_BOOKS_URL,
                params=self._params(q=query, maxResults=limit, printType="books"),
            )
        response.raise_for_status()

        items = response.json().get("items", [])
        return [self._parse(item) for item in items if item.get("volumeInfo", {}).get("title")]

    async def get_volume(self, volume_id: str) -> Optional[BookSuggestionResponse]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{GOOGLE_BOOKS_URL}/{volume_id}", params=self._params())

        # Google отвечает 404 на несуществующий и 400/503 на некорректный volume_id.
        if response.status_code in (400, 404, 503):
            return None
        response.raise_for_status()

        return self._parse(response.json())
