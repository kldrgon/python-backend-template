"""基础异常类"""


class EventFrameworkException(Exception):
    """事件框架基础异常"""
    pass


class EventPublishException(EventFrameworkException):
    """事件发布异常"""
    pass


class EventConsumeException(EventFrameworkException):
    """事件消费异常"""
    pass


class WorkflowException(EventFrameworkException):
    """Workflow异常"""
    pass


class ConfigurationException(EventFrameworkException):
    """配置异常"""
    pass
