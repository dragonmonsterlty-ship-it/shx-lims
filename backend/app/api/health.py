from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import api_response


router = APIRouter()


@router.get("")
def health_check() -> dict:
    return api_response({"status": "ok", "app": settings.app_name})
