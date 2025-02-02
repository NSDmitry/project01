from pydantic import BaseModel

class SignInResponse(BaseModel):
    message: str
    access_token: str