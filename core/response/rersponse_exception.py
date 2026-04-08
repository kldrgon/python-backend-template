from fastapi import HTTPException
from typing import Any, Optional
from .api_response import ApiResponse


class ApiResponseException(HTTPException):
    """返回ApiResponse格式的异常类。"""
    
    def __init__(
        self, 
        status_code: int = 400, 
        detail: str = "error", 
        code: Optional[int] = None,
        data: Any = None
    ):
        # 如果没有指定code，使用status_code
        response_code = code if code is not None else status_code
        
        # 创建ApiResponse格式的detail
        api_response = ApiResponse.error(
            code=response_code,
            message=detail,
            data=data
        )
        
        super().__init__(
            status_code=status_code,
            detail=api_response.model_dump()
        )