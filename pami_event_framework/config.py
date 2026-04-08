"""全局配置"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .kafka.config import KafkaConfig
from .utils import mask_url


@dataclass
class TemporalConfig:
    """Temporal配置"""
    server_url: str = "localhost:7233"
    namespace: str = "default"
    tls_config: Optional[Any] = None
    # 租户隔离：环境前缀（如 dev_zhangsan）
    env_prefix: Optional[str] = None
    
    def add_env_prefix(self, name: str) -> str:
        """为task_queue或workflow_id添加环境前缀
        
        Args:
            name: 原始名称
            
        Returns:
            带前缀的名称，格式：{env_prefix}.{name}
            如果没有配置env_prefix，返回原始名称
        """
        if self.env_prefix:
            return f"{self.env_prefix}.{name}"
        return name


@dataclass
class OutboxConfig:
    """Outbox配置"""
    batch_size: int = 100
    interval_seconds: int = 30


@dataclass
class LauncherConfig:
    """Launcher配置"""
    consumer_group_id: str = "workflow-launcher"
    # 是否支持灰度上线（使用独立Group追赶进度）
    enable_canary_group: bool = False
    canary_group_suffix: str = "-canary"
    # Topic订阅模式：
    # - "event_types": 订阅细粒度事件类型 Topic（默认）
    # - "aggregate": 订阅聚合 Topic（如 "domain_events"）
    topic_subscription_mode: str = "event_types"
    # 聚合Topic名称（仅在 aggregate 模式下使用）
    aggregate_topic_name: str = "domain_events"


@dataclass
class EventFrameworkConfig:
    """事件框架配置"""
    
    # 数据库配置
    database_url: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Kafka配置
    kafka: KafkaConfig = field(default_factory=lambda: KafkaConfig())
    
    # Temporal配置
    temporal: TemporalConfig = field(default_factory=lambda: TemporalConfig())
    
    # Outbox配置
    outbox: OutboxConfig = field(default_factory=lambda: OutboxConfig())
    
    # Launcher配置
    launcher: LauncherConfig = field(default_factory=lambda: LauncherConfig())
    
    def __repr__(self) -> str:
        return (
            f"EventFrameworkConfig(database_url={mask_url(self.database_url)!r}, "
            f"kafka={self.kafka!r}, temporal={self.temporal!r})"
        )

    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        import os
        
        return cls(
            database_url=os.getenv('WRITER_DB_URL', ''),
            db_pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            db_max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
            kafka=KafkaConfig(
                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                default_num_partitions=int(os.getenv('KAFKA_DEFAULT_PARTITIONS', '10')),
                env_prefix=os.getenv('KAFKA_ENV_PREFIX'),  # 租户隔离前缀
            ),
            temporal=TemporalConfig(
                server_url=os.getenv('TEMPORAL_HOST', 'localhost:7233'),
                namespace=os.getenv('TEMPORAL_NAMESPACE', 'default'),
                env_prefix=os.getenv('TEMPORAL_ENV_PREFIX') or os.getenv('KAFKA_ENV_PREFIX'),  # 优先用TEMPORAL_ENV_PREFIX，否则复用KAFKA_ENV_PREFIX
            ),
            outbox=OutboxConfig(
                batch_size=int(os.getenv('OUTBOX_BATCH_SIZE', '100')),
                interval_seconds=int(os.getenv('OUTBOX_INTERVAL_SECONDS', '5')),
            ),
            launcher=LauncherConfig(
                consumer_group_id=os.getenv('LAUNCHER_CONSUMER_GROUP_ID', 'workflow-launcher'),
            ),
        )

