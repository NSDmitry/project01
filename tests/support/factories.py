from __future__ import annotations

import uuid

from faker import Faker


faker = Faker()


class AuthFactory:
    @staticmethod
    def phone_number() -> str:
        return "79" + str(uuid.uuid4().int)[0:9]

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


class BookclubFactory:
    @staticmethod
    def payload(*, name: str | None = None, description: str | None = None) -> dict[str, str]:
        return {
            "name": name if name is not None else faker.pystr(min_chars=4, max_chars=99),
            "description": description if description is not None else faker.pystr(min_chars=4, max_chars=499),
        }
