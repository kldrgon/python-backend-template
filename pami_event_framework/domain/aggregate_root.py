"""聚合根基类"""

from abc import ABC, abstractmethod
from typing import List
from .domain_event import DomainEvent


class AggregateRoot(ABC):
    """
    聚合根基类

    DDD中的聚合根，负责维护业务不变式和产生领域事件。
    所有聚合根必须继承此类。
    这里的领域事件只适用于采用领域模型的上下文。
    事件是否需要被抛出由外部管理，比如在Repository的save方法中抛出。
    原因是聚合根本身并不知道自己是否已经被更新，若未更新成功，事件不应该被抛出。
    """
    
    def __init__(self):
        """初始化聚合根，创建空的事件列表"""
        self._domain_events: List[DomainEvent] = []
    
    @abstractmethod
    def get_aggregate_id(self) -> str:
        """
        获取聚合根ID（子类必须实现）
        
        用于 Outbox 记录事件时关联聚合根。
        子类应返回其业务主键，如 user_id、order_id 等。
        
        Returns:
            聚合根的唯一标识
        """
        raise NotImplementedError("子类必须实现 get_aggregate_id 方法")
    
    def raise_event(self, event: DomainEvent):
        """
        产生领域事件

        在聚合根的业务方法中调用此方法来产生领域事件。
        事件会被收集起来，在Repository保存时一并持久化到Outbox。
        不采用领域模型的轻量实现上下文，不应通过 AggregateRoot.raise_event 产生事件。

        聚合根只负责收集事件，持久化职责由外部 Repository（BaseAggregateRepository._flush_events）承担。

        Args:
            event: 领域事件实例

        示例:
            self.raise_event(OrderCreated(
                order_id=self.order_id,
                amount=self.amount
            ))
        """
        self._domain_events.append(event)
    
    def get_domain_events(self) -> List[DomainEvent]:
        """
        获取所有领域事件
        
        Returns:
            领域事件列表的副本
        """
        return self._domain_events.copy()
    
    def clear_domain_events(self):
        """
        清空领域事件
        
        在Repository保存成功后调用，防止事件重复处理
        """
        self._domain_events.clear()
    
    @property
    def has_events(self) -> bool:
        """
        检查是否有待处理的事件
        
        Returns:
            True如果有事件，False如果没有
        """
        return len(self._domain_events) > 0
