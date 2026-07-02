import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.core.errors.errors import Unauthorized, InternalServerError

# Данные инициализации старше этого срока считаем устаревшими (защита от replay).
AUTH_DATE_MAX_AGE_SECONDS = 24 * 60 * 60


def verify_init_data(init_data: str, bot_token: str) -> dict:
    """
    Проверяет подпись Telegram.WebApp.initData и возвращает данные пользователя.

    :param init_data: строка initData как есть, с клиента
    :param bot_token: токен бота, которым Telegram подписал данные
    :return: словарь user из initData
    :raises Unauthorized: подпись неверна, отсутствует или данные устарели
    """
    if not bot_token:
        raise InternalServerError(errors=["Токен Telegram-бота не настроен"])

    if not init_data:
        raise Unauthorized(errors=["Отсутствуют данные инициализации Telegram"])

    fields = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise Unauthorized(errors=["Подпись Telegram отсутствует"])

    # signature (Ed25519) не участвует в HMAC-проверке - исключаем при наличии.
    fields.pop("signature", None)

    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise Unauthorized(errors=["Неверная подпись данных Telegram"])

    auth_date = fields.get("auth_date")
    if auth_date is None or not auth_date.isdigit():
        raise Unauthorized(errors=["Некорректная дата авторизации Telegram"])

    if int(time.time()) - int(auth_date) > AUTH_DATE_MAX_AGE_SECONDS:
        raise Unauthorized(errors=["Данные авторизации Telegram устарели"])

    user_raw = fields.get("user")
    if not user_raw:
        raise Unauthorized(errors=["Данные пользователя Telegram отсутствуют"])

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        raise Unauthorized(errors=["Не удалось разобрать данные пользователя Telegram"])

    if "id" not in user:
        raise Unauthorized(errors=["В данных Telegram отсутствует идентификатор пользователя"])

    return user
