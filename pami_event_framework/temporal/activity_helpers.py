"""Activity辅助装饰器"""

from functools import wraps
from uuid import uuid4
from typing import Callable


def with_session_context(func: Callable) -> Callable:
    """
    Activity装饰器：自动管理session context
    
    用法:
        @activity.defn
        @with_session_context
        @inject
        async def my_activity(arg1, arg2):
            # 自动设置和清理 session context
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        from pami_event_framework.persistence.session import (
            set_session_context,
            reset_session_context,
            get_session,
        )
        
        session_id = str(uuid4())
        context_token = set_session_context(session_id)
        session = get_session()
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.remove()
            reset_session_context(context_token)
    
    # 保留 @activity.defn 设置的属性
    if hasattr(func, "__temporal_activity_definition"):
        wrapper.__temporal_activity_definition = func.__temporal_activity_definition
    
    return wrapper


__all__ = ['with_session_context']
