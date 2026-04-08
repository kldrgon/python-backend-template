from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from app.user.domain.domain_service import UserDomainService
from app.user.domain.usecase.user import UserUseCase

from .container import get_container

if TYPE_CHECKING:
    from app.container import Container

def get_user_domain_service(request: Request) -> UserDomainService:
    container = get_container(request)
    return container.user_domain_service()


def get_user_usecase(request: Request) -> UserUseCase:
    """UserUseCase for permission checks etc. Avoids Provide[...] to prevent circular imports."""
    container = get_container(request)
    # Prefer nested user container provider
    if hasattr(container, "user_container"):
        return container.user_container.user_command_service()
    # Fallback for older code paths
    return container.user_command_service()