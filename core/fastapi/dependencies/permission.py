from abc import ABC, abstractmethod
from typing import Type

from fastapi import Request
from fastapi.openapi.models import APIKey, APIKeyIn
from fastapi.security.base import SecurityBase


class UnauthorizedException(Exception):
    """未授权异常"""
    def __init__(self, message: str = "未授权"):
        self.message = message
        super().__init__(message)


class ForbiddenException(Exception):
    """无权限异常"""

    def __init__(self, message: str = "无权限"):
        self.message = message
        super().__init__(message)


class BasePermission(ABC):
    exception = UnauthorizedException

    @abstractmethod
    async def has_permission(self, request: Request) -> bool:
        """has permssion"""


class IsAuthenticated(BasePermission):
    exception = UnauthorizedException

    async def has_permission(self, request: Request) -> bool:
        return request.user.id is not None


class IsAdmin(BasePermission):
    exception = ForbiddenException

    async def has_permission(self, request: Request) -> bool:
        user = getattr(request, "user", None)
        if not user:
            return False
        roles = [str(item).upper() for item in (getattr(user, "roles", []) or []) if item]
        if not roles and getattr(user, "role", None):
            roles = [str(user.role).upper()]
        return "ADMIN" in roles


class AllowAll(BasePermission):
    async def has_permission(self, request: Request) -> bool:
        return True


class PermissionDependency(SecurityBase):
    def __init__(self, permissions: list[Type[BasePermission]]):
        self.permissions = permissions
        self.model: APIKey = APIKey(**{"in": APIKeyIn.header}, name="Authorization")
        self.scheme_name = self.__class__.__name__

    async def __call__(self, request: Request):
        for permission in self.permissions:
            cls = permission()
            if not await cls.has_permission(request=request):
                raise cls.exception


class RequireDatasetId(SecurityBase):
    """Dependency that extracts authorized dataset id from headers.

    Expected header: "X-Dataset-Id". Raises UnauthorizedException if missing.
    Returns the dataset id string for downstream handlers to compare against
    path params.
    """

    def __init__(self):
        self.model: APIKey = APIKey(**{"in": APIKeyIn.header}, name="X-Dataset-Id")
        self.scheme_name = self.__class__.__name__

    async def __call__(self, request: Request) -> str:
        dataset_id = request.headers.get("X-Dataset-Id") or request.headers.get("x-dataset-id")
        if not dataset_id:
            raise UnauthorizedException
        return dataset_id
