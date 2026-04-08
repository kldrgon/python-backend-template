"""Pami Event Framework - 基于Kafka和Temporal的事件驱动框架

主要特性：
- 去中心化架构，无单点故障
- 基于Kafka的Event Store，支持事件溯源
- Temporal保证Workflow幂等性和可靠性
- Outbox模式保证事件至少发送一次
- 灵活的Handler配置，支持特性开关

事件语义约定：
- `DomainEvent` 只用于采用领域模型的上下文，并应由领域模型发起
- `ApplicationEvent` 用于轻量实现上下文，由应用层显式产生
"""

from .__version__ import __version__, __author__, __description__

# Domain层
from .domain import (
    BaseEvent,
    ApplicationEvent,
    DomainEvent,
    AggregateRoot,
)

# Kafka集成
from .kafka import (
    KafkaConfig,
    KafkaEventProducer,
    KafkaEventConsumer,
)

# Temporal集成
from .temporal import (
    with_session_context,
)

# 持久化
from .persistence import (
    SessionManager,
    Base,
    get_session_context,
    set_session_context,
    reset_session_context,
    session_factory,
    Transactional,
    set_event_publisher,
    set_managed_transaction,
    is_in_managed_transaction,
    OutboxEvent,
    OutboxRepository,
    BaseAggregateRepository,
)

# 任务
from .tasks import (
    OutboxPublisher,
)

# Launcher
from .launcher import (
    WorkflowLauncher,
    SignalLauncher,
)

# 工具类
from .utils import (
    IdempotencyHelper,
    EventSerializer,
)

# 异常
from .exceptions import (
    EventFrameworkException,
    EventPublishException,
    EventConsumeException,
    WorkflowException,
    ConfigurationException,
)

# 配置
from .config import (
    EventFrameworkConfig,
    TemporalConfig,
    OutboxConfig,
    LauncherConfig,
)

__all__ = [
    # Version
    '__version__',
    '__author__',
    '__description__',
    
    # Domain
    'BaseEvent',
    'ApplicationEvent',
    'DomainEvent',
    'AggregateRoot',
    
    # Kafka
    'KafkaConfig',
    'KafkaEventProducer',
    'KafkaEventConsumer',
    
    # Temporal
    'with_session_context',
    
    # Persistence
    'SessionManager',
    'Base',
    'get_session_context',
    'set_session_context',
    'reset_session_context',
    'session_factory',
    'Transactional',
    'set_event_publisher',
    'set_managed_transaction',
    'is_in_managed_transaction',
    'OutboxEvent',
    'OutboxRepository',
    'BaseAggregateRepository',

    # Tasks
    'OutboxPublisher',
    
    # Launcher
    'WorkflowLauncher',
    'SignalLauncher',
    
    # Utils
    'IdempotencyHelper',
    'EventSerializer',
    
    # Exceptions
    'EventFrameworkException',
    'EventPublishException',
    'EventConsumeException',
    'WorkflowException',
    'ConfigurationException',
    
    # Config
    'EventFrameworkConfig',
    'TemporalConfig',
    'OutboxConfig',
    'LauncherConfig',
]
