"""Outbox表模型"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from datetime import datetime, timezone
import json

from .session import Base


class OutboxEvent(Base):
    """
    Outbox事件表
    
    用于保证事件至少被发送一次（Outbox模式）
    """
    __tablename__ = 'outbox_events'
    
    # 主键
    event_id = Column(String(36), primary_key=True, comment='事件ID')
    
    # 事件信息
    event_type = Column(String(100), nullable=False, index=True, comment='事件类型')
    event_data = Column(Text, nullable=False, comment='事件数据JSON')
    
    # 来源聚合根
    aggregate_id = Column(String(36), nullable=False, index=True, comment='聚合根ID')
    aggregate_type = Column(String(50), nullable=False, comment='聚合根类型')
    
    # 状态
    status = Column(
        String(20), 
        nullable=False, 
        default='PENDING',
        index=True,
        comment='状态: PENDING/PUBLISHED'
    )
    
    # 重试信息
    retry_count = Column(Integer, default=0, comment='重试次数')
    
    # 时间戳
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment='创建时间'
    )
    published_at = Column(DateTime(timezone=True), nullable=True, comment='发布时间')
    
    # 索引
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_aggregate', 'aggregate_type', 'aggregate_id'),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'event_data': json.loads(self.event_data) if isinstance(self.event_data, str) else self.event_data,
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type,
            'status': self.status,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }
