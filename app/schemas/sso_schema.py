from pydantic import BaseModel

class SignUpRequestModel(BaseModel):
    name: str
    phone_number: int
    password: str

class SignInRequestModel(BaseModel):
    phone_number: int
    password: str