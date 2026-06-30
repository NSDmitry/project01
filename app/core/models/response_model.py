from typing import Generic, TypeVar, Optional, List

from pydantic import Field
from pydantic import BaseModel

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    errors: List[str] = Field(default_factory=list)

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "Операция выполнена успешно") -> "ResponseModel[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str = "Произошла ошибка", errors: Optional[List[str]] = None) -> "ResponseModel[None]":
        return cls(success=False, message=message, errors=errors or [])