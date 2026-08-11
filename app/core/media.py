"""Картинки, загруженные пользователями: проверка, нормализация, хранилище.

Хранилище S3-совместимое (MinIO локально, Object Storage в проде). Пустой
S3_ENDPOINT_URL = запись в локальный каталог MEDIA_ROOT - так же, как пустой
RABBITMQ_URL означает доставку событий in-process: тесты и запуск без бакета
работают без отдельного бэкенда в коде домена.

Наружу отдаётся относительный путь /media/<ключ>, байты раздаёт само приложение
(GET /media/{key} в app/main.py). Поэтому бакет остаётся приватным, а адрес
хранилища не протекает в клиент и не зашивается в уже отданные ответы.
"""
import re
import uuid
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageOps
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.errors.errors import PayloadTooLarge, UnsupportedMediaType
from app.settings import settings

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
# Что принимаем на вход. На выходе всегда WebP: он мельче JPEG при том же
# качестве, и клиенту не нужно знать, в чём прислали исходник.
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
CONTENT_TYPE = "image/webp"

AVATARS = "avatars"
CLUB_COVERS = "club-covers"

# Максимальная сторона после уменьшения. Обложка крупнее: она тянется на всю
# карточку клуба, аватар показывается небольшим кружком в списках.
MAX_SIDE = {AVATARS: 512, CLUB_COVERS: 1200}

# Ключ приходит из URL при раздаче. Без проверки формы «../» в нём вылез бы за
# пределы каталога локального хранилища.
_KEY_PATTERN = re.compile(rf"^({AVATARS}|{CLUB_COVERS})/[0-9a-f]{{32}}\.webp$")


def media_url(key: str | None) -> str | None:
    """Ссылка для ответа API. None - картинки нет."""
    return f"/media/{key}" if key else None


async def store_image(prefix: str, upload: UploadFile) -> str:
    """Проверяет и уменьшает картинку, кладёт в хранилище, отдаёт её ключ."""
    # read(лимит + 1): в память попадает максимум лимит плюс байт, которым он и
    # ловится - размер не берём из Content-Length, его клиент может соврать.
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise PayloadTooLarge(f"Файл больше {MAX_UPLOAD_BYTES // 1024 // 1024} МБ")

    key = f"{prefix}/{uuid.uuid4().hex}.webp"
    # Декодирование картинки и запись в хранилище блокирующие - уводим в пул
    # потоков, иначе на каждой загрузке встаёт event loop целиком.
    await run_in_threadpool(_normalize_and_put, key, data, MAX_SIDE[prefix])

    return key


async def read_image(key: str) -> bytes | None:
    """Байты картинки. None - ключ не той формы или файла нет."""
    if not _KEY_PATTERN.match(key):
        return None

    return await run_in_threadpool(_get, key)


async def delete_image(key: str | None) -> None:
    """Удаляет файл, если он есть. Пустой ключ и мусор игнорирует."""
    if not key or not _KEY_PATTERN.match(key):
        return

    await run_in_threadpool(_delete, key)


def _normalize_and_put(key: str, data: bytes, max_side: int) -> None:
    _put(key, _to_webp(data, max_side))


def _to_webp(data: bytes, max_side: int) -> bytes:
    try:
        source = Image.open(BytesIO(data))
    except Exception:
        # Тип определяет декодер по сигнатуре файла, а не Content-Type запроса:
        # заголовок и расширение подделываются, содержимое - нет.
        raise UnsupportedMediaType("Файл не является изображением")

    if source.format not in ALLOWED_FORMATS:
        raise UnsupportedMediaType("Поддерживаются только JPEG, PNG и WebP")

    try:
        # Съёмка с телефона иначе лежит на боку: ориентация в EXIF, не в пикселях.
        image: Image.Image = ImageOps.exif_transpose(source) or source
        # RGB/RGBA WebP умеет сам. Палитру, оттенки серого и CMYK переводим -
        # RGBA не трогаем, иначе прозрачный фон стал бы чёрным.
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        image.thumbnail((max_side, max_side))

        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=82)
    except Exception:
        # Битый или обрезанный файл: сигнатура на месте, а пиксели не читаются.
        raise UnsupportedMediaType("Не удалось прочитать изображение")

    return buffer.getvalue()


@lru_cache(maxsize=1)
def _client() -> Any:
    # Импорт внутри функции: без S3 (тесты, локальный запуск) boto3 не нужен и
    # его секунда на импорт не тратится.
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


def _local_path(key: str) -> Path:
    return Path(settings.media_root) / key


def _put(key: str, data: bytes) -> None:
    if not settings.s3_endpoint_url:
        path = _local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return

    _client().put_object(
        Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=CONTENT_TYPE
    )


def _get(key: str) -> bytes | None:
    if not settings.s3_endpoint_url:
        path = _local_path(key)
        return path.read_bytes() if path.is_file() else None

    client = _client()
    try:
        return cast(bytes, client.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read())
    except client.exceptions.NoSuchKey:
        return None


def _delete(key: str) -> None:
    if not settings.s3_endpoint_url:
        _local_path(key).unlink(missing_ok=True)
        return

    _client().delete_object(Bucket=settings.s3_bucket, Key=key)
