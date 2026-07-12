from app.books.schemas import BookSuggestionResponse
from app.books.deps import get_google_books_client
from app.main import app


def suggestion(volume_id: str = "vol-1", title: str = "Мастер и Маргарита", **kwargs) -> BookSuggestionResponse:
    defaults = dict(
        author="Михаил Булгаков",
        description="Роман о визите дьявола в Москву",
        genres="Fiction, Classics",
        published_year=1967,
    )
    defaults.update(kwargs)
    return BookSuggestionResponse(volume_id=volume_id, title=title, **defaults)


class FakeGoogleBooksClient:
    """Замена GoogleBooksClient в тестах - без походов в сеть."""

    def __init__(self, volumes: list[BookSuggestionResponse] | None = None) -> None:
        self.volumes = {v.volume_id: v for v in (volumes or [])}
        self.get_volume_calls = 0

    async def search(self, query: str, limit: int = 10) -> list[BookSuggestionResponse]:
        return list(self.volumes.values())

    async def get_volume(self, volume_id: str) -> BookSuggestionResponse | None:
        self.get_volume_calls += 1
        return self.volumes.get(volume_id)


def install_fake_google(volumes: list[BookSuggestionResponse] | None = None) -> FakeGoogleBooksClient:
    # Снимается вместе с остальными override-ами в teardown фикстуры client.
    fake = FakeGoogleBooksClient(volumes)
    app.dependency_overrides[get_google_books_client] = lambda: fake
    return fake
