"""幂等性工具"""

import hashlib
from typing import Any, Dict


class IdempotencyHelper:
    """幂等性辅助工具"""
    
    @staticmethod
    def generate_workflow_id(handler_name: str, event_id: str) -> str:
        """
        生成Workflow ID
        
        格式: {handler_name}-{event_id}
        
        Args:
            handler_name: Handler名称
            event_id: 事件ID
            
        Returns:
            Workflow ID
        """
        return f"{handler_name}-{event_id}"
    
    @staticmethod
    def generate_idempotency_key(
        operation: str,
        *args,
        **kwargs
    ) -> str:
        """
        生成幂等性键
        
        Args:
            operation: 操作名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            幂等性键（SHA256哈希）
        """
        # 构建字符串表示
        parts = [operation]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        content = ":".join(parts)
        
        # 生成哈希
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def is_duplicate(key: str, cache: Dict[str, Any]) -> bool:
        """
        检查是否重复
        
        Args:
            key: 幂等性键
            cache: 缓存字典
            
        Returns:
            是否重复
        """
        return key in cache
    
    @staticmethod
    def mark_processed(key: str, cache: Dict[str, Any], value: Any = True):
        """
        标记为已处理
        
        Args:
            key: 幂等性键
            cache: 缓存字典
            value: 缓存值
        """
        cache[key] = value
