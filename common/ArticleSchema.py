from pydantic import BaseModel

class ArticleSchema(BaseModel):
    title: str
    description: str
    rating: int
    author: str

    class Config:
        orm_mode = True