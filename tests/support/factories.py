from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import date, timedelta
from urllib.parse import urlencode

from faker import Faker


faker = Faker()

# Токен фиктивного бота, общий для генерации initData в тестах и для настройки
# приложения через фикстуру telegram_bot_token.
TELEGRAM_TEST_BOT_TOKEN = "123456:TEST-telegram-bot-token"


class AuthFactory:
    @staticmethod
    def phone_number() -> str:
        return "+79" + str(uuid.uuid4().int)[0:9]

    @classmethod
    def register_payload(
        cls,
        *,
        name: str = "Test User",
        phone_number: str | int | None = None,
        password: str = "ValidPass1",
    ) -> dict[str, str | int]:
        return {
            "name": name,
            "phone_number": phone_number or cls.phone_number(),
            "password": password,
        }

    @staticmethod
    def login_payload(*, phone_number: str | int, password: str) -> dict[str, str | int]:
        return {
            "phone_number": phone_number,
            "password": password,
        }


class UserFactory:
    @staticmethod
    def update_payload(*, name: str, phone_number: str | int) -> dict[str, str | int]:
        return {
            "name": name,
            "phone_number": phone_number,
        }

    @staticmethod
    def change_password_payload(*, current_password: str, new_password: str) -> dict[str, str]:
        return {
            "current_password": current_password,
            "new_password": new_password,
        }


class TelegramFactory:
    @staticmethod
    def user(**overrides) -> dict:
        user = {
            "id": uuid.uuid4().int % (10 ** 12),
            "first_name": "Telegram",
            "username": "tg_user",
        }
        user.update(overrides)
        return user

    @staticmethod
    def init_data(
        *,
        bot_token: str = TELEGRAM_TEST_BOT_TOKEN,
        user: dict | None = None,
        auth_date: int | None = None,
        tamper_hash: bool = False,
    ) -> str:
        user = user if user is not None else TelegramFactory.user()
        fields = {
            "auth_date": str(auth_date if auth_date is not None else int(time.time())),
            "query_id": "AAEtest",
            "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
        }

        data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        signature = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        fields["hash"] = "0" * 64 if tamper_hash else signature
        return urlencode(fields)


class BookclubFactory:
    @staticmethod
    def payload(
        *,
        name: str | None = None,
        description: str | None = None,
        genres: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "name": name if name is not None else faker.pystr(min_chars=4, max_chars=99),
            "description": description if description is not None else faker.pystr(min_chars=4, max_chars=499),
            "genres": genres if genres is not None else ["fiction"],
        }


class GenreFactory:
    @staticmethod
    def payload(
        *,
        code: str | None = None,
        name: str | None = None,
        sort_order: int = 0,
    ) -> dict[str, object]:
        unique = uuid.uuid4().hex[:8]
        return {
            "code": code if code is not None else f"test-genre-{unique}",
            "name": name if name is not None else f"Test Genre {unique}",
            "sort_order": sort_order,
        }


class ReadingFactory:
    @staticmethod
    def stage(*, title: str = "Главы 1-5", due_in_days: int = -1, end_page: int | None = None) -> dict[str, object]:
        return {
            "title": title,
            "due_date": str(date.today() + timedelta(days=due_in_days)),
            "end_page": end_page,
        }

    @staticmethod
    def schedule_payload(
        *,
        started_in_days: int = -10,
        deadline_in_days: int = 10,
        stages: list[dict] | None = None,
    ) -> dict[str, object]:
        # Сроки и этапы без книги - тело закрытия голосования, книгу там выбирают
        # голоса. По умолчанию срок первого этапа уже прошёл, второго - ещё нет: с
        # таким заходом проверяется и «в графике», и отставание.
        default_stages = [
            ReadingFactory.stage(title="Главы 1-5", due_in_days=-1, end_page=100),
            ReadingFactory.stage(title="Главы 6-10", due_in_days=5, end_page=200),
        ]
        return {
            "started_at": str(date.today() + timedelta(days=started_in_days)),
            "deadline": str(date.today() + timedelta(days=deadline_in_days)),
            "stages": stages if stages is not None else default_stages,
        }

    @staticmethod
    def payload(
        *,
        book_volume_id: str = "vol-1",
        started_in_days: int = -10,
        deadline_in_days: int = 10,
        stages: list[dict] | None = None,
    ) -> dict[str, object]:
        return {
            "book_volume_id": book_volume_id,
            **ReadingFactory.schedule_payload(
                started_in_days=started_in_days,
                deadline_in_days=deadline_in_days,
                stages=stages,
            ),
        }


class ThreadFactory:
    @staticmethod
    def create_payload(
        *,
        club_id: int,
        title: str | None = None,
        content: str | None = None,
        reading_stage_id: int | None = None,
    ) -> dict[str, str | int]:
        payload: dict[str, str | int] = {
            "title": title if title is not None else faker.sentence(nb_words=4),
            "content": content if content is not None else faker.paragraph(),
            "club_id": club_id,
        }
        if reading_stage_id is not None:
            payload["reading_stage_id"] = reading_stage_id

        return payload

    @staticmethod
    def update_payload(*, title: str | None = None, content: str | None = None) -> dict[str, str]:
        return {
            "title": title if title is not None else faker.sentence(nb_words=4),
            "content": content if content is not None else faker.paragraph(),
        }


class CommentFactory:
    @staticmethod
    def create_payload(*, content: str | None = None) -> dict[str, str]:
        return {
            "content": content if content is not None else faker.paragraph(),
        }

    @staticmethod
    def update_payload(*, content: str | None = None) -> dict[str, str]:
        return {
            "content": content if content is not None else faker.paragraph(),
        }
