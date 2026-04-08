import re
from pydantic import BaseModel, Field, field_validator


class Etag(BaseModel):
    """用于对象版本控制与缓存的 ETag 值对象。"""
    
    value: str = Field(..., description="ETag 值")
    
    @field_validator("value")
    @classmethod
    def validate_etag(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ETag 不能为空")
        
        # 移除可能存在的引号（ETag 常以引号包裹）
        cleaned = v.strip().strip('"')
        
        if not cleaned:
            raise ValueError("清理后 ETag 仍为空")
        
        # 基础校验 - ETag 通常为十六进制字符串，或包含短横线/字母数字
        if not re.match(r"^[a-fA-F0-9\-_]+$", cleaned):
            raise ValueError(f"ETag 格式非法: {v}")
        
        return cleaned
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Etag):
            return self.value == other.value
        if isinstance(other, str):
            # Handle comparison with quoted ETags
            other_cleaned = other.strip().strip('"')
            return self.value == other_cleaned
        return False
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    @property
    def quoted(self) -> str:
        """以引号包裹的 ETag（HTTP 标准格式）。"""
        return f'"{self.value}"'
    
    def is_weak(self) -> bool:
        """是否为弱验证 ETag（以 W/ 开头）。"""
        return self.value.startswith("W/")
    
    def is_strong(self) -> bool:
        """是否为强验证 ETag。"""
        return not self.is_weak()
