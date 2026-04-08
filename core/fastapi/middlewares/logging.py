"""
请求日志中间件

功能：
1. 为每个请求绑定 correlation_id (request_id)
2. 记录请求/响应元数据（method、path、status、duration）
3. 自动清理上下文变量（避免协程间污染）

使用纯 ASGI 实现，避免 BaseHTTPMiddleware 导致的 event loop 跨 Task 问题。
"""
import time
from typing import Callable

import structlog
from asgi_correlation_id.context import correlation_id
from starlette.types import ASGIApp, Receive, Scope, Send


logger = structlog.stdlib.get_logger("api.access")


class LoggingMiddleware:
    """请求日志中间件（纯 ASGI，避免 asyncpg/redis 跨 loop 问题）"""

    def __init__(self, app: ASGIApp, slow_threshold_ms: int = 200) -> None:
        self.app = app
        self.slow_threshold_ms = slow_threshold_ms

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()
        request_id = correlation_id.get()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                if request_id is not None:
                    headers = list(message.get("headers", []))
                    headers.append((b"x-request-id", request_id.encode()))
                    headers.append(
                        (b"x-process-time-ms", str(int((time.perf_counter() - start_time) * 1000)).encode())
                    )
                    message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("Request handler exception")
            raise
        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            method = scope.get("method", "UNKNOWN")
            path = scope.get("path", "")
            query_string = scope.get("query_string", b"").decode()
            client = scope.get("client")
            client_host = client[0] if client else "unknown"
            client_port = client[1] if client else 0
            http_version = scope.get("http_version", "1.1")
            url = f"http://{scope.get('server', ('', 0))[0]}{path}"
            if query_string:
                url += f"?{query_string}"

            log_method = logger.warning if status_code >= 400 else logger.info
            if duration_ms >= self.slow_threshold_ms:
                log_method = logger.warning

            log_method(
                f'{client_host}:{client_port} - "{method} {path} HTTP/{http_version}" {status_code}',
                http={
                    "method": method,
                    "path": path,
                    "query_string": query_string,
                    "url": url,
                    "status_code": status_code,
                    "version": http_version,
                },
                network={"client": {"ip": client_host, "port": client_port}},
                duration_ms=duration_ms,
            )
