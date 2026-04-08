"""Kafka配置"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class KafkaConfig:
    """Kafka连接配置"""
    
    # 连接配置
    bootstrap_servers: str = "localhost:9092"
    
    # Producer配置
    producer_config: Dict[str, Any] = field(default_factory=dict)
    
    # Consumer配置
    consumer_config: Dict[str, Any] = field(default_factory=dict)
    
    # Partition数量（创建Topic时使用）
    default_num_partitions: int = 10
    
    # 副本因子
    default_replication_factor: int = 1
    
    # 租户隔离：环境前缀（如 dev_zhangsan）
    env_prefix: Optional[str] = None
    
    # 安全配置（可选）
    security_protocol: Optional[str] = None
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"KafkaConfig(bootstrap_servers={self.bootstrap_servers!r}, "
            f"sasl_username={self.sasl_username!r}, "
            f"sasl_password={'***' if self.sasl_password else None!r}, "
            f"env_prefix={self.env_prefix!r})"
        )

    def get_producer_config(self) -> Dict[str, Any]:
        """获取Producer配置"""
        config = {
            'bootstrap_servers': self.bootstrap_servers,
            'acks': 'all',  # 所有副本确认
            'enable_idempotence': True,  # 幂等性（自动保证顺序和去重）
            **self.producer_config
        }
        
        if self.security_protocol:
            config['security_protocol'] = self.security_protocol
        if self.sasl_mechanism:
            config['sasl_mechanism'] = self.sasl_mechanism
        if self.sasl_username:
            config['sasl_plain_username'] = self.sasl_username
        if self.sasl_password:
            config['sasl_plain_password'] = self.sasl_password
            
        return config
    
    def get_consumer_config(self, group_id: str) -> Dict[str, Any]:
        """获取Consumer配置"""
        config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.add_env_prefix(group_id),
            'auto_offset_reset': 'earliest',  # 从最早开始消费
            'enable_auto_commit': False,  # 手动提交offset
            **self.consumer_config
        }
        
        if self.security_protocol:
            config['security_protocol'] = self.security_protocol
        if self.sasl_mechanism:
            config['sasl_mechanism'] = self.sasl_mechanism
        if self.sasl_username:
            config['sasl_plain_username'] = self.sasl_username
        if self.sasl_password:
            config['sasl_plain_password'] = self.sasl_password
            
        return config
    
    def add_env_prefix(self, name: str) -> str:
        """为topic或group_id添加环境前缀
        
        Args:
            name: 原始名称（topic或group_id）
            
        Returns:
            带前缀的名称，格式：{env_prefix}.{name}
            如果没有配置env_prefix，返回原始名称
        """
        if self.env_prefix:
            return f"{self.env_prefix}.{name}"
        return name
