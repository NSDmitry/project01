---
title: "Architecture overview"
status: accepted
tags:
  - "architecture"
  - "architecture-overview"
---

12 modules across 5 domains; Python; FastAPI; SQLAlchemy/PostgreSQL; pytest

| Area | Type | Covers |
|---|---|---|
| Stack | rule | язык, фреймворк, персистентность, тест-раннер |
| Running locally | guide | install / run / test |
| Entry points | doc | HTTP-роуты по доменам, worker, cron, migrate |
| Domains | doc | границы и размеры 5 доменов + core |
| Data model: iam | doc | сущности и связи |
| Data model: bookclubs | doc | сущности и связи |
| Data model: threads | doc | сущности и связи |
| Data model: books | doc | сущности и связи |
| Data model: genres | doc | сущности и связи |
| Integrations | doc | Redis, RabbitMQ, S3-хранилище, Telegram, Google Books |
| Configuration | doc | имена env-переменных и назначение |
| Hotspot: iam-service | spec | контракт аутентификации, сессий, пользователей |
| Hotspot: threads-service | spec | контракт тредов, комментариев, лайков |
| Hotspot: threads-router | spec | HTTP-контракт threads |
| Hotspot: bookclubs-router | spec | HTTP-контракт bookclubs |
| Hotspot: iam-router | spec | HTTP-контракт IAM |
| Hotspot: threads-repository | spec | контракт хранения threads |
| Hotspot: bookclubs-repository | spec | контракт хранения bookclubs |
| Hotspot: iam-repository | spec | контракт хранения IAM |
| Hotspot: bookclubs-service | spec | контракт бизнес-логики bookclubs |
| Hotspot: core-events | spec | контракт событийной шины |
| Hotspot: core-media | spec | контракт загруженных картинок и файлового хранилища |
| Hotspot specs: +1 more | spec | genres-router (HTTP-контракт справочника жанров) |
| auth | rule | авторизация хендлеров через get_current_user |
| errors | rule | ошибки через иерархию app/core/errors |
| architecture | rule | кросс-доменные порты и события, не импорты |
| graphify | rule | imported convention |
| coding principles | rule | imported convention |
| punctuation | rule | imported convention |