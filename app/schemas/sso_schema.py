from pydantic import BaseModel, field_validator

from app.core.validators import validate_e164

class SignUpRequest(BaseModel):
    name: str
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class SignInRequest(BaseModel):
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class TelegramAuthRequest(BaseModel):
    init_data: str
