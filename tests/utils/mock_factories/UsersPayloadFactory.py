

class UsersPayloadFactory:
    @staticmethod
    def make_change_user_info_payload(name: str, phone_number: int) -> dict:
        return {
            "name": name,
            "phone_number": phone_number
        }