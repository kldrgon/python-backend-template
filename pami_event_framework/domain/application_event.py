"""应用事件基类"""

from .base_event import BaseEvent


class ApplicationEvent(BaseEvent):
    """
    应用事件基类。

    用于不采用领域模型的轻量实现上下文。
    这类事件由应用层显式产生，不应命名为领域事件。
    若需要异步投递，可由应用层显式写入 Outbox。
    """
