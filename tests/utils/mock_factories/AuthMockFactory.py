import uuid

class AuthMockFactory:
    @staticmethod
    def make_register_payload(
        name: str = "Тестовый пользователь",
        phone_number: str = None,
        password: str = "123456"
    ):
        return {
            "name": name,
            "phone_number": phone_number or str(AuthMockFactory.generate_random_phone_number()),
            "password": password
    }

    @staticmethod
    def make_login_payload(
        phone_number: str,
        password: str
    ):
        return {
            "phone_number": phone_number,
            "password": password
        }

    @staticmethod
    def generate_random_phone_number() -> str:
        return "79" + str(uuid.uuid4().int)[0:9]