from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.user.domain.exception.errors import (
    InvalidEmailError,
    WeakPasswordError,
    EmptyNicknameError,
    DuplicateEmailOrNicknameError,
)
from core.response.api_response import ApiResponse

def register_user_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidEmailError)
    async def _invalid_email_error_handler(request: Request, exc: InvalidEmailError):
        return JSONResponse(status_code=400, content=ApiResponse.error(code=400, message=str(exc)).model_dump())

    @app.exception_handler(WeakPasswordError)
    async def _weak_password_error_handler(request: Request, exc: WeakPasswordError):
        return JSONResponse(status_code=400, content=ApiResponse.error(code=400, message=str(exc)).model_dump())

    @app.exception_handler(EmptyNicknameError)
    async def _empty_nickname_error_handler(request: Request, exc: EmptyNicknameError):
        return JSONResponse(status_code=400, content=ApiResponse.error(code=400, message=str(exc)).model_dump())

    @app.exception_handler(DuplicateEmailOrNicknameError)
    async def _duplicate_email_or_nickname_error_handler(request: Request, exc: DuplicateEmailOrNicknameError):
        return JSONResponse(status_code=409, content=ApiResponse.error(code=409, message=str(exc)).model_dump())
