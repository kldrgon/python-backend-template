from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request

from core.fastapi.dependencies.permission import UnauthorizedException

ANONYMOUS_ID_HEADER = "X-Anonymous-Id"


@dataclass(frozen=True)
class ApiPrincipal:
    principal_type: str
    principal_id: str
    is_anonymous: bool


def resolve_optional_principal(*, request: Request) -> ApiPrincipal | None:
    user = getattr(request, "user", None)
    user_id = getattr(user, "id", None)
    if user_id:
        return ApiPrincipal(
            principal_type="USER",
            principal_id=str(user_id),
            is_anonymous=False,
        )

    anonymous_id = read_anonymous_id(request=request)
    if anonymous_id:
        return ApiPrincipal(
            principal_type="ANONYMOUS",
            principal_id=anonymous_id,
            is_anonymous=True,
        )
    return None


def require_principal(*, request: Request) -> ApiPrincipal:
    principal = resolve_optional_principal(request=request)
    if principal is None:
        raise UnauthorizedException("需要登录或提供 X-Anonymous-Id")
    return principal


def require_user_principal(*, request: Request) -> ApiPrincipal:
    principal = resolve_optional_principal(request=request)
    if principal is None or principal.is_anonymous:
        raise UnauthorizedException("需要登录")
    return principal


def resolve_or_create_anonymous_principal(*, request: Request) -> tuple[ApiPrincipal, str | None]:
    principal = resolve_optional_principal(request=request)
    if principal is not None:
        return principal, None
    generated = uuid4().hex
    return (
        ApiPrincipal(
            principal_type="ANONYMOUS",
            principal_id=generated,
            is_anonymous=True,
        ),
        generated,
    )


def read_anonymous_id(*, request: Request) -> str | None:
    raw = request.headers.get(ANONYMOUS_ID_HEADER) or request.headers.get(ANONYMOUS_ID_HEADER.lower())
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    if len(value) > 64:
        raise UnauthorizedException("X-Anonymous-Id 长度不能超过 64")
    return value
