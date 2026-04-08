from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.adapter.input.api import router as auth_router
from app.auth.adapter.input.api.exception_handler import register_auth_exception_handlers
from app.blob.adapter.input.api import router as blob_router
from app.bootstrap_web import get_web_bootstrap, shutdown_web_bootstrap
from app.container import Container
from app.user.adapter.input.api import router as user_router
from app.user.adapter.input.api.exception_handler import register_user_exception_handlers
from core.config import config
from core.fastapi.dependencies import Logging
from core.fastapi.middlewares import (
    AuthBackend,
    AuthenticationMiddleware,
    ResponseLogMiddleware,
    SQLAlchemyMiddleware,
    LoggingMiddleware,
)
from core.helpers.cache import Cache, CustomKeyMaker, RedisBackend

WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """应用生命周期管理"""
    # Startup: 初始化 Web Bootstrap
    web_bootstrap = await get_web_bootstrap()
    
    # 初始化 Container（此时 WebBootstrap 已完全初始化）
    container = Container()
    container.init_resources()
    # 这里为了让 FastAPI 的 Provide/@inject 生效，仍然对整个 app 做 wiring。
    # 副作用是会连带 import app.*.event_handler.activities，导致 API 启动时出现
    # "Registered activity" 日志；当前仅记录该现象，行为暂不收窄。
    container.wire(packages=["app", "core.fastapi.dependencies"])
    app_.container = container  # type: ignore[attr-defined]
    
    auth_router.container = container
    blob_router.container = container
    user_router.container = container

    yield
    
    # Shutdown: 关闭 Web Bootstrap
    await shutdown_web_bootstrap()


def init_routers(app_: FastAPI) -> None:
    app_.include_router(user_router)
    app_.include_router(auth_router)
    app_.include_router(blob_router)

def init_listeners(app_: FastAPI) -> None:
    register_auth_exception_handlers(app_)
    register_user_exception_handlers(app_)


def on_auth_error(request: Request, exc: Exception):
    """认证中间件的错误处理函数"""
    from core.response.rersponse_exception import ApiResponseException
    from core.response.api_response import ApiResponse
    from fastapi.responses import JSONResponse
    
    # 如果已经是 ApiResponseException，直接返回
    if isinstance(exc, ApiResponseException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    
    # 其他异常统一处理
    return JSONResponse(
        status_code=401,
        content=ApiResponse.error(code=401, message=str(exc)).model_dump(),
    )


def make_middleware() -> list[Middleware]:
    from asgi_correlation_id import CorrelationIdMiddleware
    
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(CorrelationIdMiddleware),  # 必须在 LoggingMiddleware 之前，确保 request_id 已就绪
        Middleware(LoggingMiddleware),
        Middleware(
            AuthenticationMiddleware,
            backend=AuthBackend(),
            on_error=on_auth_error,
        ),
        Middleware(SQLAlchemyMiddleware),
        # TraceMiddleware 和 ResponseLogMiddleware 功能已整合到 LoggingMiddleware
    ]
    return middleware


def init_cache() -> None:
    Cache.init(backend=RedisBackend(), key_maker=CustomKeyMaker())


def create_app() -> FastAPI:
    app_ = FastAPI(
        title="Nana",
        description="Hide API",
        version="1.0.0",
        docs_url=None if config.app.env == "production" else "/docs",
        redoc_url=None if config.app.env == "production" else "/redoc",
        dependencies=[Depends(Logging)],
        middleware=make_middleware(),
        lifespan=lifespan,
    )
    

    init_routers(app_=app_)
    init_listeners(app_=app_)
    init_cache()
    return app_


app = create_app()
