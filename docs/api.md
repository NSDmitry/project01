# API

Обзор всех ручек сервиса. Для защищённых методов используется заголовок `X-Session-Id`, а не `Authorization: Bearer` - подробнее в [Аутентификация и сессии](auth.md).

## Аутентификация

- `POST /api/auth/register` - регистрация по имени, номеру телефона и паролю; в ответе только `session_id`
- `POST /api/auth/login` - вход по номеру телефона и паролю; в ответе только `session_id`
- `POST /api/auth/telegram` - вход и регистрация через Telegram Mini App по подписанным данным `initData`; в ответе только `session_id`
- `POST /api/auth/logout` - завершение текущей сессии по заголовку `X-Session-Id`

Профиль пользователя auth-ручки не возвращают - его нужно запрашивать отдельно через `GET /api/users/current`.

## Пользователи

- `GET /api/users/current` - профиль текущего пользователя (`id`, `name`, `phone_number`, `created_at`)
- `GET /api/users/public?user_id=...` - публичный профиль пользователя (только `id` и `name`, без номера телефона)
- `PUT /api/users` - обновление имени и номера телефона, в ответе - обновлённый профиль текущего пользователя
- `PUT /api/users/password` - смена пароля с завершением всех активных сессий

## Книжные клубы

- `POST /api/bookclubs` - создать клуб
- `GET /api/bookclubs` - получить список клубов; параметр `relation=owner` - клубы, где пользователь владелец, `relation=member` - клубы, в которых он состоит
- `GET /api/bookclubs/{club_id}` - получить клуб по `id`
- `DELETE /api/bookclubs/{club_id}` - удалить клуб
- `POST /api/bookclubs/{club_id}/join` - вступить в клуб
- `DELETE /api/bookclubs/{club_id}/leave` - выйти из клуба

## Треды

- `GET /api/threads/{club_id}` - получить треды клуба
- `POST /api/threads` - создать тред
- `PUT /api/threads/{thread_id}` - обновить тред
- `DELETE /api/threads/{thread_id}` - удалить тред

## Комментарии

- `GET /api/threads/{thread_id}/comments` - получить комментарии треда (постранично, старые сверху)
- `POST /api/threads/{thread_id}/comments` - создать комментарий; требует авторизации и членства в клубе (как у тредов)
- `PUT /api/comments/{comment_id}` - редактировать комментарий; только автор
- `DELETE /api/comments/{comment_id}` - удалить комментарий; автор либо владелец клуба
