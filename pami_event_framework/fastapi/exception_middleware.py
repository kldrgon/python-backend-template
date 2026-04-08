"""异常处理中间件"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..exceptions import EventFrameworkException


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    统一异常处理中间件

    职责：
    - 捕获 EventFrameworkException 并转换为 JSON 响应
    - 捕获其他未知异常并返回 500 错误
    - 放行 HTTPException，保留原始状态码（404/403/422 等）

    使用示例:
        app.add_middleware(ExceptionHandlerMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except StarletteHTTPException:
            # 放行 HTTP 异常（404/403/422 等），由 FastAPI 默认处理
            raise
        except EventFrameworkException as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": 500,
                    "error_code": e.__class__.__name__,
                    "message": str(e),
                    "data": None,
                },
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": 500,
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": str(e),
                    "data": None,
                },
            )
