import jwt
from pydantic import BaseModel, Field
from starlette.authentication import AuthenticationBackend
from starlette.middleware.authentication import (
    AuthenticationMiddleware as BaseAuthenticationMiddleware,
)
from starlette.requests import HTTPConnection

from core.config import config


class CurrentUser(BaseModel):
    id: str = Field(None, description="ID")
    role: str | None = Field(None, description="主角色（大写）")
    roles: list[str] = Field(default_factory=list, description="角色列表（大写）")


class AuthBackend(AuthenticationBackend):
    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[bool, CurrentUser | None]:
        current_user = CurrentUser()
        authorization: str = conn.headers.get("Authorization")
        # logging.info(f"-----------------------{authorization}------------------------") 
        if not authorization:
            return False, current_user

        try:
            scheme, credentials = authorization.split(" ")
            if scheme.lower() != "bearer":
                return False, current_user
        except ValueError:
            return False, current_user

        if not credentials:
            return False, current_user

        try:
            payload = jwt.decode(
                credentials,
                config.jwt.secret_key,
                algorithms=[config.jwt.algorithm],
            )
            user_id = payload.get("user_id")
            payload_roles = payload.get("roles")
            payload_role = payload.get("role")
        except jwt.exceptions.PyJWTError:
            return False, current_user

        current_user.id = user_id
        roles: list[str] = []
        if isinstance(payload_roles, list):
            roles = [str(item).upper() for item in payload_roles if item]
        elif payload_role:
            roles = [str(payload_role).upper()]
        current_user.roles = roles
        current_user.role = roles[0] if roles else None
        return True, current_user


class AuthenticationMiddleware(BaseAuthenticationMiddleware):
    pass
