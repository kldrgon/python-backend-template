"""后台任务模块"""

from .outbox_publisher import OutboxPublisher

__all__ = [
    'OutboxPublisher',
]
