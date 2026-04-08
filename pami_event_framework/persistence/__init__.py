"""持久化模块"""

from .session import (
    SessionManager,
    Base,
    get_session_context,
    set_session_context,
    reset_session_context,
    session_factory,
)
from .transactional import (
    Transactional,
    set_event_publisher,
    set_managed_transaction,
    is_in_managed_transaction,
)
from .outbox_model import OutboxEvent
from .outbox_repository import OutboxRepository
from .base_aggregate_repository import BaseAggregateRepository

__all__ = [
    # Session
    'SessionManager',
    'Base',
    'get_session_context',
    'set_session_context',
    'reset_session_context',
    'session_factory',
    # Transactional
    'Transactional',
    'set_event_publisher',
    'set_managed_transaction',
    'is_in_managed_transaction',
    # Outbox
    'OutboxEvent',
    'OutboxRepository',
    # Repository 基类
    'BaseAggregateRepository',
]
