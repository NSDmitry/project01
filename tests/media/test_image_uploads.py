from io import BytesIO

import pytest
from PIL import Image

from app.core import media
from app.settings import settings
from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow, BookclubFlow


def png(size: tuple[int, int] = (32, 32), color: str = "red") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format="PNG")

    return buffer.getvalue()


@pytest.fixture(autouse=True)
def media_root(tmp_path):
    # S3_ENDPOINT_URL в тестах пуст - хранилище пишет в каталог. Подставляем
    # временный, чтобы файлы теста уезжали вместе с ним.
    original = settings.media_root
    settings.media_root = str(tmp_path)
    yield
    settings.media_root = original


class TestAvatarUpload:
    def test_upload_returns_url_and_serves_image(self, api):
        auth = AuthFlow.register(api)

        response = api.upload_avatar(png(), headers=auth.headers)

        assert_status_code(response, 200)
        avatar_url = response.json()["data"]["avatar_url"]
        assert avatar_url.startswith("/media/avatars/")

        image = api.media(avatar_url)
        assert_status_code(image, 200)
        # На выходе всегда WebP, независимо от формата загруженного файла.
        assert image.headers["content-type"] == "image/webp"
        assert Image.open(BytesIO(image.content)).format == "WEBP"

    def test_avatar_visible_in_own_and_public_profile(self, api):
        auth = AuthFlow.register(api)
        avatar_url = api.upload_avatar(png(), headers=auth.headers).json()["data"]["avatar_url"]

        current = api.current_user(headers=auth.headers).json()["data"]
        public = api.public_user(auth.user_id, headers=auth.headers).json()["data"]

        assert current["avatar_url"] == avatar_url
        assert public["avatar_url"] == avatar_url

    def test_second_upload_replaces_previous_file(self, api):
        auth = AuthFlow.register(api)
        first_url = api.upload_avatar(png(), headers=auth.headers).json()["data"]["avatar_url"]

        second_url = api.upload_avatar(png(color="blue"), headers=auth.headers).json()["data"]["avatar_url"]

        assert second_url != first_url
        # Прежний файл удаляется - иначе хранилище растёт с каждой загрузкой.
        assert_status_code(api.media(first_url), 404)
        assert_status_code(api.media(second_url), 200)

    def test_upload_requires_authorization(self, api):
        assert_status_code(api.upload_avatar(png()), 401)


class TestClubCoverUpload:
    def test_owner_uploads_cover_and_it_comes_in_the_card(self, api):
        auth = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=auth).json()["data"]
        assert club["cover_url"] is None

        response = api.upload_bookclub_cover(club["id"], png(), headers=auth.headers)

        assert_status_code(response, 200)
        cover_url = response.json()["data"]["cover_url"]
        assert cover_url.startswith("/media/club-covers/")
        assert api.bookclub(club["id"], headers=auth.headers).json()["data"]["cover_url"] == cover_url
        assert_status_code(api.media(cover_url), 200)

    def test_not_owner_cannot_upload_cover(self, api):
        owner = AuthFlow.register(api)
        club = BookclubFlow.create(api, auth=owner).json()["data"]
        stranger = AuthFlow.register(api)

        response = api.upload_bookclub_cover(club["id"], png(), headers=stranger.headers)

        assert_status_code(response, 403)
        assert api.bookclub(club["id"], headers=owner.headers).json()["data"]["cover_url"] is None

    def test_unknown_club_is_not_found(self, api):
        auth = AuthFlow.register(api)

        assert_status_code(api.upload_bookclub_cover(10**9, png(), headers=auth.headers), 404)


class TestUploadValidation:
    def test_not_an_image_is_rejected(self, api):
        auth = AuthFlow.register(api)

        # Content-Type заявлен картинкой - решает содержимое, а не заголовок.
        response = api.upload_avatar(b"not an image at all", headers=auth.headers)

        assert_status_code(response, 415)

    def test_unsupported_format_is_rejected(self, api):
        auth = AuthFlow.register(api)
        buffer = BytesIO()
        Image.new("RGB", (32, 32)).save(buffer, format="BMP")

        response = api.upload_avatar(buffer.getvalue(), headers=auth.headers, filename="avatar.bmp")

        assert_status_code(response, 415)

    def test_oversized_file_is_rejected(self, api):
        auth = AuthFlow.register(api)

        response = api.upload_avatar(b"\0" * (media.MAX_UPLOAD_BYTES + 1), headers=auth.headers)

        assert_status_code(response, 413)

    def test_large_image_is_downscaled(self, api):
        auth = AuthFlow.register(api)

        avatar_url = api.upload_avatar(
            png(size=(2000, 1000)), headers=auth.headers
        ).json()["data"]["avatar_url"]

        stored = Image.open(BytesIO(api.media(avatar_url).content))
        assert max(stored.size) == media.MAX_SIDE[media.AVATARS]

    async def test_key_outside_storage_is_not_served(self):
        # Ключ приходит из URL: путь с «..» не должен вылезать из каталога.
        assert await media.read_image("../../../etc/passwd") is None
        assert await media.read_image("avatars/../../etc/passwd") is None
