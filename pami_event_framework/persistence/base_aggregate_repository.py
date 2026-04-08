"""聚合根仓储基类"""

import structlog
from ..domain.aggregate_root import AggregateRoot
from .session import get_session
from .outbox_repository import OutboxRepository
from .transactional import add_transaction_event

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class BaseAggregateRepository:
    """
    聚合根仓储基类

    封装"取事件 -> 写 Outbox -> 清空"三步，子类只需在 save() 末尾调用
    `await self._flush_events(aggregate)`，无需依赖任何中间件实例。
    """

    async def _flush_events(self, aggregate: AggregateRoot, session=None) -> None:
        """
        将聚合根持有的领域事件写入 Outbox，并注册到当前事务事件列表。

        Args:
            aggregate: 持有领域事件的聚合根实例
        """
        events = aggregate.get_domain_events()
        if not events:
            return

        active_session = session or get_session()
        if not active_session:
            raise RuntimeError("未找到当前会话，无法保存事件到Outbox")

        outbox_repo = OutboxRepository(active_session)
        outbox_events = await outbox_repo.save_events(
            events=events,
            aggregate_id=aggregate.get_aggregate_id(),
            aggregate_type=aggregate.__class__.__name__,
        )

        for e in outbox_events:
            add_transaction_event(e)

        aggregate.clear_domain_events()

        logger.info(
            "outbox_events_collected",
            count=len(events),
            aggregate_type=aggregate.__class__.__name__,
            aggregate_id=aggregate.get_aggregate_id(),
        )
