from typing import Dict

class BookclubPayloadFactory:
    @staticmethod
    def create_bookclub_payload(name: str = "default_bookclub_id", description: str = "Default Book Club") -> Dict:
        return {
            "name": name,
            "description": description
        }