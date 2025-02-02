from pydantic import BaseModel

class SignInRequest(BaseModel):
    phone_number: str
    password: str