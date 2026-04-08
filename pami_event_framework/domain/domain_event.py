"""领域事件基类"""

from .base_event import BaseEvent


class DomainEvent(BaseEvent):
    """
    领域事件基类

    只用于采用领域模型的上下文。
    领域事件必须由领域模型内部发起，例如聚合根或实体行为触发。
    不采用领域模型的轻量实现上下文，不应使用 DomainEvent 语义。
    """
