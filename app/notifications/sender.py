"""Каналы доставки уведомлений.

Канал - это функция (user, text) -> bool | None:
    True  - доставлено,
    False - канал применим, но попытка не удалась (воркер повторит),
    None  - канал к пользователю неприменим (нет привязки).

Новый провайдер (email, sms, push) подключается малой кровью: функция с той же
сигнатурой здесь плюс строка в CHANNELS в tasks.py. Воркер сам разберётся,
кому из пользователей канал доступен.
"""
import logging

import httpx

from app.iam.models import User
from app.settings import settings

logger = logging.getLogger("app.notifications")

TELEGRAM_API_URL = "https://api.telegram.org"


async def send_telegram(user: User, text: str) -> bool | None:
    if user.telegram_id is None:
        return None

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан - Telegram-уведомления не отправляются")
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": user.telegram_id, "text": text},
            )
    except httpx.HTTPError as error:
        logger.warning("Telegram недоступен: %s", error)
        return False

    if response.status_code != 200:
        # Типичный случай - 403: пользователь заблокировал бота. Повторы упрутся
        # в MAX_ATTEMPTS и строка перестанет выбираться.
        logger.warning("Telegram ответил %s: %s", response.status_code, response.text)
        return False

    return True
