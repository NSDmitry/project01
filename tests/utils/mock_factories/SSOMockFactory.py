import uuid

class SSOMockFactory:
    @staticmethod
    def make_sign_up_payload(name: str = "Тестовый пользователь", phone_number: str = None, password: str = "123456"):
        return {
            "name": name,
            "phone_number": phone_number or str(SSOMockFactory.generate_random_phone_number()),
            "password": password
    }

    @staticmethod
    def make_sign_in_payload(phone_number: str, password: str):
        return {
            "phone_number": phone_number,
            "password": password
        }

    @staticmethod
    def generate_random_phone_number() -> str:
        return "79" + str(uuid.uuid4().int)[0:9]