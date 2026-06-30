from pydantic import BaseModel, field_validator

from app.core.validators import validate_e164

class SignUpRequestModel(BaseModel):
    name: str
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class SignInRequestModel(BaseModel):
    phone_number: str
    password: str

    _validate_phone = field_validator("phone_number")(validate_e164)

class TelegramAuthRequestModel(BaseModel):
    init_data: str
