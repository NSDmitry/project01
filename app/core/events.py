"""Кросс-доменные события через RabbitMQ.

Домены не импортируют друг друга: издатель делает publish(event, payload),
подписчики регистрируются декоратором subscribe в своих модулях events.py
(импортируются в app.main ради side-effect регистрации).

Без настроенного RABBITMQ_URL (тесты, локальный запуск без брокера) события
доставляются синхронно в том же процессе - семантика "к ответу всё почищено".
"""
import json
import logging

import aio_pika

from app.core.database import AsyncSessionLocal
from app.settings import settings

logger = logging.getLogger(__name__)

EXCHANGE = "domain_events"

# Имена событий - единственное место, где они объявлены. Опечатка в строке-литерале
# дала бы молча неработающего подписчика.
USER_DELETED = "user_deleted"
CLUBS_DELETED = "clubs_deleted"
GENRES_DELETED = "genres_deleted"
THREAD_CREATED = "thread_created"
THREAD_DELETED = "thread_deleted"

# {событие: [(очередь, хендлер)]}
_handlers: dict[str, list] = {}

# Хендлеры работают вне запроса, поэтому открывают свою сессию БД и коммитят
# сами. Тесты подменяют фабрику на свою (как override get_db в conftest).
session_factory = AsyncSessionLocal

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None


def subscribe(event: str, queue: str):
    """Подписать хендлер на событие.

    queue - очередь домена-подписчика: при распиле монолита на сервисы очередь
    уезжает вместе со своим доменом, топология не меняется.
    """
    def wrap(fn):
        _handlers.setdefault(event, []).append((queue, fn))
        return fn
    return wrap


async def publish(event: str, payload: dict) -> None:
    if _exchange is None:
        for _, fn in _handlers.get(event, []):
            await fn(payload)
        return
    await _exchange.publish(
        aio_pika.Message(
            json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=event,
    )


async def startup() -> None:
    global _connection, _exchange
    if not settings.rabbitmq_url:
        return
    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await _connection.channel()
    _exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

    # Сообщения упавших хендлеров не теряем и не зацикливаем - в dead-letter очередь.
    dlx = await channel.declare_exchange(f"{EXCHANGE}.dlx", aio_pika.ExchangeType.FANOUT, durable=True)
    dlq = await channel.declare_queue(f"{EXCHANGE}.dead", durable=True)
    await dlq.bind(dlx)

    # Группируем хендлеры по очереди: {очередь: {событие: хендлер}}. На каждый
    # домен - одна очередь с одним consumer, который диспетчеризует по routing_key.
    by_queue: dict[str, dict] = {}
    for event, pairs in _handlers.items():
        for queue_name, fn in pairs:
            by_queue.setdefault(queue_name, {})[event] = fn

    for queue_name, event_handlers in by_queue.items():
        queue = await channel.declare_queue(
            queue_name, durable=True, arguments={"x-dead-letter-exchange": f"{EXCHANGE}.dlx"}
        )
        for event in event_handlers:
            await queue.bind(_exchange, routing_key=event)
        await queue.consume(_consumer(event_handlers))


def _consumer(handlers: dict):
    async def consume(message: aio_pika.abc.AbstractIncomingMessage) -> None:
        try:
            await handlers[message.routing_key](json.loads(message.body))
            await message.ack()
        except Exception:
            logger.exception("Событие %s не обработано", message.routing_key)
            await message.reject(requeue=False)  # уходит в DLQ
    return consume


async def shutdown() -> None:
    global _connection, _exchange
    if _connection is not None:
        await _connection.close()
        _connection = None
        _exchange = None
