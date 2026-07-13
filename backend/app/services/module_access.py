from fastapi import HTTPException, status

from app.core.modules import MODULE_VALUES, parse_modules
from app.models.user import User


def ensure_module(user: User, module: str) -> None:
    if module not in MODULE_VALUES:
        raise ValueError(f"Unknown module: {module}")
    if user.role == "admin":
        return
    if module not in parse_modules(user.modules):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Module access required: {module}",
        )
