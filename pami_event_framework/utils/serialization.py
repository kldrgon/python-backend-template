"""事件序列化工具"""

import json
from typing import Dict, Any
from datetime import datetime
from ..domain.domain_event import DomainEvent


class EventSerializer:
    """事件序列化工具"""
    
    @staticmethod
    def serialize_event(event: DomainEvent) -> str:
        """
        序列化事件为JSON字符串
        
        Args:
            event: 领域事件
            
        Returns:
            JSON字符串
        """
        event_dict = event.to_dict()
        return json.dumps(event_dict, ensure_ascii=False)
    
    @staticmethod
    def deserialize_event(json_str: str) -> Dict[str, Any]:
        """
        反序列化JSON字符串为事件字典
        
        Args:
            json_str: JSON字符串
            
        Returns:
            事件字典
        """
        return json.loads(json_str)
    
    @staticmethod
    def serialize_dict(data: Dict[str, Any]) -> str:
        """
        序列化字典为JSON字符串
        
        Args:
            data: 字典数据
            
        Returns:
            JSON字符串
        """
        # 处理datetime对象
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        return json.dumps(data, ensure_ascii=False, default=json_serial)
    
    @staticmethod
    def deserialize_dict(json_str: str) -> Dict[str, Any]:
        """
        反序列化JSON字符串为字典
        
        Args:
            json_str: JSON字符串
            
        Returns:
            字典数据
        """
        return json.loads(json_str)
