"""事务装饰器"""

import asyncio
import structlog
from functools import wraps
from contextvars import ContextVar
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from .outbox_model import OutboxEvent

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# 标记当前是否在外部事务管理中
_in_managed_transaction: ContextVar[bool] = ContextVar(
    "in_managed_transaction", 
    default=False
)

# 记录当前事务收集的事件对象列表（None 表示未激活，避免可变默认值被跨协程共享）
_current_transaction_events: ContextVar[Optional[List["OutboxEvent"]]] = ContextVar(
    "current_transaction_events",
    default=None
)

_outbox_publisher = None


def add_transaction_event(event: "OutboxEvent") -> None:
    """添加当前事务收集的事件对象"""
    events = _current_transaction_events.get()
    if events is None:
        _current_transaction_events.set([event])
    else:
        events.append(event)


def get_transaction_events() -> List["OutboxEvent"]:
    """获取当前事务收集的事件对象列表"""
    return _current_transaction_events.get() or []


def clear_transaction_events() -> None:
    """清空当前事务收集的事件对象列表"""
    _current_transaction_events.set(None)


def set_event_publisher(publisher) -> None:
    """注册 OutboxPublisher 实例，事务提交后会自动触发一次 publish_once"""
    global _outbox_publisher
    _outbox_publisher = publisher


def _fire_publish_once() -> None:
    """事务提交成功后，fire-and-forget 触发一次 outbox 发布"""
    publisher = _outbox_publisher
    if publisher is None:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_safe_publish_once(publisher))
    except RuntimeError:
        pass


async def _safe_publish_once(publisher) -> None:
    try:
        await publisher.publish_once()
    except BaseException:
        logger.warning("post_commit_publish_once_failed", exc_info=True)


def set_managed_transaction(value: bool) -> None:
    """设置当前是否在外部管理的事务中"""
    _in_managed_transaction.set(value)


def is_in_managed_transaction() -> bool:
    """检查当前是否在外部管理的事务中"""
    return _in_managed_transaction.get()


class Transactional:
    """
    事务装饰器
    
    特性：
    - API请求：每个方法独立管理事务
    - Consumer/Worker：由外部中间件统一管理事务
    - 事务提交后：仅保证 Outbox 落库，发布由后台 OutboxPublisher 处理
    
    使用示例:
        # 使用当前上下文 session
        @Transactional()
        async def create_order(self, order_data):
            pass
    """
    
    def __init__(self):
        """初始化"""
    
    def __call__(self, func):
        @wraps(func)
        async def _transactional(*args, **kwargs):
            session = None
            try:
                from .session import get_session, get_session_context
                get_session_context()
                session = get_session()
            except (LookupError, RuntimeError):
                session = None
            
            # 检查是否在外部管理的事务中
            in_managed = is_in_managed_transaction()
            
            # 清空事件列表（每个事务开始时）
            if not in_managed:
                clear_transaction_events()
            
            try:
                result = await func(*args, **kwargs)
                
                # 只有不在外部管理的事务中才执行commit
                if not in_managed and session is not None:
                    await session.commit()
                    if get_transaction_events():
                        _fire_publish_once()
                
                return result
                
            except Exception as e:
                # 只有不在外部管理的事务中才执行rollback
                if not in_managed and session is not None:
                    await session.rollback()
                raise e
            
            finally:
                # 关键修复：无论成功或失败，都清理 session
                # 只在非外部管理的事务中清理（外部管理的由中间件清理）
                if not in_managed and session is not None:
                    await session.remove()
                    # 清空事件列表
                    clear_transaction_events()

        return _transactional
