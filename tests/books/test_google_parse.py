from app.books.google_client import GoogleBooksClient


def _item(**volume_info) -> dict:
    return {"id": "vol-1", "volumeInfo": {"title": "Мастер и Маргарита", **volume_info}}


class TestGoogleParse:
    def test_takes_thumbnail_and_page_count(self):
        book = GoogleBooksClient._parse(_item(
            imageLinks={"smallThumbnail": "https://g/small", "thumbnail": "https://g/big"},
            pageCount=480,
        ))

        assert book.cover_url == "https://g/big"
        assert book.page_count == 480

    def test_falls_back_to_small_thumbnail(self):
        book = GoogleBooksClient._parse(_item(imageLinks={"smallThumbnail": "https://g/small"}))

        assert book.cover_url == "https://g/small"

    def test_rewrites_http_cover_to_https(self):
        book = GoogleBooksClient._parse(_item(imageLinks={"thumbnail": "http://g/big?u=http://x"}))

        assert book.cover_url == "https://g/big?u=http://x"

    def test_missing_cover_and_pages_are_none(self):
        book = GoogleBooksClient._parse(_item())

        assert book.cover_url is None
        assert book.page_count is None

    def test_zero_page_count_is_none(self):
        book = GoogleBooksClient._parse(_item(pageCount=0))

        assert book.page_count is None
