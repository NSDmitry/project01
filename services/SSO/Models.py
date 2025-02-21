from pydantic import BaseModel

from services.User.Models import PublicUserResponseModel


class SingUpRequestModel(BaseModel):
    name: str
    phone_number: int
    password: str

class SignInRequestModel(BaseModel):
    phone_number: int
    password: str

class SignInResponseModel(BaseModel):
    message: str
    access_token: str
    model: PublicUserResponseModel