"""
数据库 Session 配置
复用 pami_event_framework 的运行时层
"""
from sqlalchemy.ext.asyncio import AsyncSession
from pami_event_framework.persistence.session import (
    Base,
    session_factory,
    get_session_context,
    set_session_context,
    reset_session_context,
    get_session as get_framework_session,
)


def get_session():
    """
    获取当前 session
    
    注意：首次调用会触发 runtime 懒加载初始化
    """
    return get_framework_session()


class _SessionProxy:
    """
    Session 代理，延迟获取实际 session
    
    支持直接导入使用：from core.db import session
    """
    
    def __getattr__(self, name):
        return getattr(get_session(), name)
    
    def __call__(self, *args, **kwargs):
        return get_session()(*args, **kwargs)
    
    def __await__(self):
        return get_session().__await__()
    
    def __repr__(self):
        return f"<SessionProxy -> {get_session()!r}>"


# 直接导入使用：from core.db import session
session : AsyncSession = _SessionProxy()
