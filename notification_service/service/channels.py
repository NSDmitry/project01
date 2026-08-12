"""Каналы доставки уведомлений.

Канал - это функция (chat-реквизиты, text) -> bool | None:
    True  - доставлено,
    False - канал применим, но попытка не удалась (воркер повторит),
    None  - канал к получателю неприменим (нет привязки).

Новый провайдер (email, sms, push) подключается функцией с той же сигнатурой
плюс строкой в CHANNELS в worker.py - без изменения приёма, схемы и relay.
"""
import logging

import httpx

from service.settings import settings

logger = logging.getLogger("service.channels")

TELEGRAM_API_URL = "https://api.telegram.org"


async def send_telegram(chat_id: int | None, text: str) -> bool | None:
    if chat_id is None:
        return None

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан - Telegram-уведомления не отправляются")
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
    except httpx.HTTPError as error:
        logger.warning("Telegram недоступен: %s", error)
        return False

    if response.status_code != 200:
        # Типичный случай - 403: получатель заблокировал бота. Повторы упрутся
        # в MAX_ATTEMPTS и строка перестанет выбираться.
        logger.warning("Telegram ответил %s: %s", response.status_code, response.text)
        return False

    return True
