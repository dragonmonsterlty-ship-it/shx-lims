from typing import Any, Generic, TypeVar

from pydantic import BaseModel


ResponseData = TypeVar("ResponseData")


class ApiResponse(BaseModel, Generic[ResponseData]):
    code: int = 0
    message: str = "ok"
    data: ResponseData


def api_response(data: Any = None, message: str = "ok", code: int = 0) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}
