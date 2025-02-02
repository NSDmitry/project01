from pydantic import BaseModel

class User(BaseModel):
    name: str
    phone_number: str
    password: str