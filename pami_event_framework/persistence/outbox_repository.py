"""Outbox仓储"""

import json
import structlog
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from .outbox_model import OutboxEvent
from ..domain.base_event import BaseEvent

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class OutboxRepository:
    """Outbox事件仓储（异步）"""
    
    def __init__(self, session: AsyncSession):
        """
        初始化仓储
        
        Args:
            session: SQLAlchemy异步会话
        """
        self.session = session
    
    async def save_event(
        self,
        event: BaseEvent,
        aggregate_id: str,
        aggregate_type: str
    ) -> OutboxEvent:
        """
        保存事件到Outbox
        
        Args:
            event: 事件对象。采用领域模型时通常是 DomainEvent，轻量实现时也可由应用层显式传入 ApplicationEvent
            aggregate_id: 聚合根ID
            aggregate_type: 聚合根类型
            
        Returns:
            Outbox事件记录
        """
        event_dict = event.to_dict()
        
        outbox_event = OutboxEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            event_data=json.dumps(event_dict),
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            status='PENDING',
            retry_count=0,
            created_at=datetime.now(timezone.utc)
        )
        
        self.session.add(outbox_event)
        await self.session.flush()
        
        logger.debug("outbox_event_saved", event_id=event.event_id, event_type=event.event_type)
        
        return outbox_event
    
    async def save_events(
        self,
        events: List[BaseEvent],
        aggregate_id: str,
        aggregate_type: str
    ) -> List[OutboxEvent]:
        """
        批量保存事件到Outbox
        
        Args:
            events: 事件列表
            aggregate_id: 聚合根ID
            aggregate_type: 聚合根类型
            
        Returns:
            Outbox事件记录列表
        """
        outbox_events = []
        
        for event in events:
            outbox_event = await self.save_event(event, aggregate_id, aggregate_type)
            outbox_events.append(outbox_event)
        
        return outbox_events
    
    async def get_pending_events(self, limit: int = 100) -> List[OutboxEvent]:
        """
        获取待发布的事件

        使用 SELECT FOR UPDATE SKIP LOCKED 避免多实例并发重复处理同一批事件。

        Args:
            limit: 最大数量

        Returns:
            待发布的事件列表
        """
        stmt = (
            select(OutboxEvent)
            .filter(OutboxEvent.status == 'PENDING')
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def mark_as_published(self, event_id: str):
        """
        标记事件为已发布

        Args:
            event_id: 事件ID
        """
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.event_id == event_id)
            .values(status='PUBLISHED', published_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        logger.debug("outbox_event_marked_published", event_id=event_id)
    
    async def increment_retry_count(self, event_id: str):
        """
        增加重试次数（失败时调用，但保持PENDING状态继续重试）

        Args:
            event_id: 事件ID
        """
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.event_id == event_id)
            .values(retry_count=OutboxEvent.retry_count + 1)
        )
        await self.session.execute(stmt)
        logger.warning("outbox_event_retry_incremented", event_id=event_id)
    
    async def delete_published_events(self, days: int = 7) -> int:
        """
        删除已发布的旧事件（清理）
        
        Args:
            days: 保留天数
            
        Returns:
            删除的事件数量
        """
        from datetime import timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        stmt = delete(OutboxEvent).filter(
            OutboxEvent.status == 'PUBLISHED',
            OutboxEvent.published_at < cutoff_time
        )
        result = await self.session.execute(stmt)
        count = result.rowcount
        
        if count > 0:
            await self.session.flush()
            logger.info("outbox_old_events_deleted", count=count)
        
        return count
