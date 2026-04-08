from __future__ import annotations
import logging
from typing import Optional

from fastapi import HTTPException, Request, status

from core.fastapi.middlewares.authentication import CurrentUser


def get_current_user_id_optional(request: Request) -> Optional[str]:
    user: CurrentUser | None = getattr(request, "user", None)
    if user and getattr(user, "id", None) is not None:
        return str(user.id)
    return None


def require_admin(request: Request) -> None:
    user: CurrentUser | None = getattr(request, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    role_values = [str(item).upper() for item in (getattr(user, "roles", []) or []) if item]
    if not role_values and getattr(user, "role", None):
        role_values = [str(user.role).upper()]

    if "ADMIN" not in role_values:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


