from fastapi import status
from fastapi.responses import JSONResponse
from typing import List, Optional
from app.core.models.response_model import ResponseModel

class APIException(Exception):
    def __init__(
        self,
        message: str = "Произошла ошибка",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        errors: Optional[List[str]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []

    def as_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content=ResponseModel.error_response(
                message=self.message,
                errors=self.errors
            ).dict()
        )