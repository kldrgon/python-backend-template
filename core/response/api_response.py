from pydantic import BaseModel, Field
from typing import Generic, Optional, TypeVar, Any

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=200, description="业务状态码, 默认使用http状态码 ， 自定义状态码请使用4位数字")
    data: Optional[T] = Field(default=None, description="数据负载")
    message: str = Field(default="success", description="消息")
    
    #预设成功
    @classmethod
    def success(cls, data: Any = None, message: str = "success", code: int = 200) -> "ApiResponse[Any]":
        """创建成功响应。"""
        return cls(code=code, data=data, message=message)


    
    @classmethod
    def created(cls, code: int = 201, data: Any = None, message: str = "created") -> "ApiResponse[Any]":
        """创建响应。"""
        return cls(code=code, data=data, message=message)

    #预设错误响应
    @classmethod
    def error(cls, code: int = 400, message: str = "error", data: Any = None) -> "ApiResponse[Any]":
        """创建错误响应。"""
        return cls(code=code, data=data, message=message)

# Ensure Pydantic resolves any forward references for generic usages at import time
try:  # guard for potential import cycles in some execution contexts
    ApiResponse.model_rebuild()
except Exception:
    pass