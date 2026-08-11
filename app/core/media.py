"""Картинки, загруженные пользователями: проверка, нормализация, хранилище.

Хранилище S3-совместимое (MinIO локально, Object Storage в проде). Пустой
S3_ENDPOINT_URL = запись в локальный каталог MEDIA_ROOT: тесты и запуск без
бакета работают без отдельного бэкенда в коде домена.

Наружу отдаётся относительный путь /media/<ключ>, байты раздаёт само приложение
(GET /media/{key} в app/main.py). Поэтому бакет остаётся приватным, а адрес
хранилища не протекает в клиент и не зашивается в уже отданные ответы.
"""
import logging
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
# Потолок числа пикселей. Байты его не ограничивают: сжатый файл на сотню
# килобайт разворачивается в растр на гигабайт, а дефолтный предохранитель Pillow
# (89 млн пикселей) до двойного превышения только предупреждает. 40 млн - это
# 6300x6300, заведомо больше любой обложки и аватара.
MAX_PIXELS = 40_000_000
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

    # Размер известен из заголовка, пиксели ещё не читались - отсекаем до декода,
    # иначе картинка успевает занять память, которой у процесса нет.
    width, height = source.size
    if width * height > MAX_PIXELS:
        raise PayloadTooLarge(f"Изображение больше {MAX_PIXELS // 1_000_000} млн пикселей")

    try:
        # JPEG декодер умеет уменьшать на лету - просим его сразу отдать картинку
        # около нужного размера. Иначе фото с телефона (4000x3000) разворачивается
        # целиком, чтобы через строку быть выброшенным в 512 px. Делаем до
        # exif_transpose: он читает пиксели, и после него черновик уже не поможет.
        source.draft(None, (max_side, max_side))
        # Съёмка с телефона иначе лежит на боку: ориентация в EXIF, не в пикселях.
        image: Image.Image = ImageOps.exif_transpose(source) or source
        # RGB/RGBA WebP умеет сам, остальное переводим. Прозрачность сохраняем:
        # у палитры она живёт в info, у полутонового - вторым каналом (LA), и
        # convert("RGB") залил бы вырезанный фон цветом палитры.
        if image.mode not in ("RGB", "RGBA"):
            has_alpha = image.mode in ("LA", "PA") or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")

        image.thumbnail((max_side, max_side))

        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=82)
    except Exception:
        # Битый или обрезанный файл: сигнатура на месте, а пиксели не читаются.
        # Логируем с трейсом: сюда же попадёт и наша поломка (нет кодека, кончилась
        # память), а клиенту в обоих случаях уходит один и тот же отказ.
        logging.getLogger("app").warning("Не удалось обработать изображение", exc_info=True)

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
    except client.exceptions.ClientError as error:
        # Ключ, которого нет, хранилище отдаёт по-разному: NoSuchKey, если у ключа
        # доступа есть право листинга, и 403 AccessDenied, если нет. Оба случая для
        # клиента - «картинки нет». Остальные ошибки хранилища летят в 500 как есть.
        if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "NoSuchBucket", "404", "403", "AccessDenied"):
            return None

        raise


def _delete(key: str) -> None:
    if not settings.s3_endpoint_url:
        _local_path(key).unlink(missing_ok=True)
        return

    _client().delete_object(Bucket=settings.s3_bucket, Key=key)
