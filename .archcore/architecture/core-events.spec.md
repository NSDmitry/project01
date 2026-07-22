---
title: "Core events: кросс-доменная событийная шина"
status: accepted
tags:
  - "core"
  - "events"
  - "spec"
---

## Purpose & Scope
Контракт событийной шины @app/core/events.py - единственного канала кросс-доменных изменений данных. Потребители - все домены: издатели (`publish`) и подписчики (`subscribe`). Вне scope: содержимое обработчиков (спеки доменных репозиториев).

## Surface
- `publish(event, payload)`, декоратор `subscribe(event, queue)`, `startup()`, `shutdown()`.
- События (объявлены только здесь): `USER_DELETED`, `CLUBS_DELETED`, `GENRES_DELETED`, `THREAD_CREATED`, `THREAD_DELETED`.
- Exchange `domain_events` (topic, durable) + dead-letter `domain_events.dlx` / очередь `domain_events.dead`.
- `session_factory` - фабрика сессий БД для хендлеров (тесты подменяют).

## Normative Behavior
1. Издатель MUST публиковать события через `publish`; домены MUST NOT импортировать друг друга для доставки изменений.
2. Имя события MUST браться из констант этого модуля; строковые литералы MUST NOT использоваться (опечатка = молча неработающий подписчик).
3. WHEN `RABBITMQ_URL` не задан, `publish` MUST вызвать всех подписчиков синхронно в том же процессе (семантика "к ответу всё почищено").
4. WHEN `RABBITMQ_URL` задан, `publish` MUST отправить persistent-сообщение в exchange `domain_events` с routing_key = имя события.
5. `startup` MUST объявить на каждый домен одну durable-очередь с одним consumer, диспетчеризующим по routing_key; очереди MUST иметь dead-letter exchange.
6. Хендлер MUST открывать собственную сессию БД через `session_factory` и коммитить сам - он работает вне HTTP-запроса.

## Constraints & Invariants
- Инвариант: доставка at-least-once - обработчики MUST быть идемпотентны или защищены (пример: `GREATEST(threads_count + delta, 0)` в bookclubs).
- Инвариант: очередь принадлежит домену-подписчику; при распиле монолита очередь уезжает вместе с доменом, топология не меняется.

## Failure Behavior
1. IF хендлер бросает исключение (режим RabbitMQ), THEN consumer MUST отклонить сообщение без requeue - оно уходит в DLQ `domain_events.dead`, не зацикливается и не теряется.
2. IF событие не имеет подписчиков, THEN `publish` MUST завершиться без ошибки.

## Conformance
Реализация конформна, когда выполняет поведения 1-6, держит инварианты at-least-once и принадлежности очередей и правила отказов 1-2. Синхронный fallback проверяется всем тестовым контуром (тесты работают без брокера).