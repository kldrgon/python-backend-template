"""SQLAlchemy中间件"""

from uuid import uuid4
from starlette.types import ASGIApp, Receive, Scope, Send

from ..persistence import set_session_context, reset_session_context
from ..persistence.session import get_session


class SQLAlchemyMiddleware:
    """
    SQLAlchemy Session中间件
    
    职责：
    - 为每个请求创建独立的Session上下文
    - 请求结束后自动清理Session
    
    使用示例:
        from pami_event_framework.fastapi import SQLAlchemyMiddleware
        
        # 自动使用当前 session runtime
        app.add_middleware(SQLAlchemyMiddleware)
    """
    
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        session_id = str(uuid4())
        context = set_session_context(session_id=session_id)

        try:
            await self.app(scope, receive, send)
        except Exception:
            session = get_session()
            await session.rollback()
            raise
        finally:
            session = get_session()
            await session.remove()
            reset_session_context(context=context)
