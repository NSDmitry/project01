from typing import Dict
from faker import Faker

faker = Faker()

class BookclubPayloadFactory:
    @staticmethod
    def create_bookclub_payload(name: str = faker.pystr(min_chars=4, max_chars=99), description: str = faker.pystr(min_chars=4, max_chars=499)) -> Dict:
        return {
            "name": name,
            "description": description
        }