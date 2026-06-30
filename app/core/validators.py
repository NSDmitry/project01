import re

_E164_RE = re.compile(r"^\+[1-9]\d{9,14}$")
E164_ERROR = "Номер телефона должен быть в формате E.164, например +79991234567"


def validate_e164(phone_number: str) -> str:
    if not phone_number or not _E164_RE.fullmatch(phone_number):
        raise ValueError(E164_ERROR)
    return phone_number
