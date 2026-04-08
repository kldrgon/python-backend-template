from fastapi import FastAPI, Request

from app.auth.application.exception import InvalidRefreshTokenException
from core.exceptions import DecodeTokenException, ExpiredTokenException
from core.fastapi.dependencies.permission import ForbiddenException, UnauthorizedException
from core.response.rersponse_exception import ApiResponseException


def register_auth_exception_handlers(app: FastAPI) -> None:
    """注册认证相关的异常处理器，捕获异常并抛出 ApiResponseException"""
    
    @app.exception_handler(DecodeTokenException)
    async def decode_token_exception_handler(request: Request, exc: DecodeTokenException):
        raise ApiResponseException(
            status_code=401,
            detail=str(exc),
            code=4011  # 业务错误码：Access Token 无效或解码失败
        )
    
    @app.exception_handler(ExpiredTokenException)
    async def expired_token_exception_handler(request: Request, exc: ExpiredTokenException):
        raise ApiResponseException(
            status_code=401,
            detail=str(exc),
            code=4012  # 业务错误码：Access Token 已过期
        )
    
    @app.exception_handler(InvalidRefreshTokenException)
    async def invalid_refresh_token_exception_handler(request: Request, exc: InvalidRefreshTokenException):
        raise ApiResponseException(
            status_code=401,
            detail=str(exc),
            code=4013  # 业务错误码：Refresh Token 无效（需要重新登录）
        )
    
    @app.exception_handler(UnauthorizedException)
    async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
        raise ApiResponseException(
            status_code=401,
            detail=exc.message,
            code=4010  # 业务错误码：未授权
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
        raise ApiResponseException(
            status_code=403,
            detail=exc.message,
            code=4030,  # 业务错误码：无权限
        )

