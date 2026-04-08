from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO, AsyncIterator, Tuple

from pydantic import BaseModel

from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.etag import Etag
from app.blob.domain.vo.mime_type import MimeType


class ObjectMetadata(BaseModel):
    """存储操作返回的对象元数据（领域层抽象，不依赖具体存储实现）。"""

    size_bytes: int
    etag: Etag
    mime_type: Optional[MimeType] = None
    last_modified: Optional[str] = None  # ISO 格式日期时间字符串
    storage_class: Optional[str] = None
    custom_metadata: Optional[Dict[str, str]] = None


class StorageAdapter(ABC):
    """Blob 域的存储适配器抽象端口。

    注意：这是领域层接口，具体实现位于 adapter/output/storage/* 中。
    """

    @abstractmethod
    async def put_object(
        self,
        locator: StorageLocator,
        body: BinaryIO,
        *,
        mime_type: Optional[MimeType] = None,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: Optional[str] = None,
    ) -> ObjectMetadata:
        """将对象存储到后端存储系统。"""
        ...

    @abstractmethod
    async def head_object(self, locator: StorageLocator) -> Optional[ObjectMetadata]:
        """获取对象元数据而不下载内容。"""
        ...

    @abstractmethod
    async def delete_object(self, locator: StorageLocator) -> bool:
        """从存储中删除对象。"""
        ...

    @abstractmethod
    async def object_exists(self, locator: StorageLocator) -> bool:
        """检查对象是否在存储中存在。"""
        ...

    @abstractmethod
    async def get_object_url(
        self,
        locator: StorageLocator,
        *,
        expires_in_seconds: Optional[int] = None,
        skip_exists_check: bool = False,
    ) -> str:
        """生成访问对象的 URL。
        
        Args:
            locator: 存储位置定位器
            expires_in_seconds: URL过期时间（秒）
            skip_exists_check: 是否跳过存在性检查以提升性能，默认 False
        """
        ...

    # ==========================
    # 可选能力：服务端拷贝（优先）
    # ==========================

    def supports_copy(self) -> bool:
        """是否支持服务端 copy（例如 S3 CopyObject / MinIO CopyObject）。默认不支持。"""
        return False

    async def copy_object(
        self,
        *,
        source: StorageLocator,
        target: StorageLocator,
    ) -> ObjectMetadata:
        """
        将 source 对象复制到 target（服务端拷贝，避免下载+上传）。
        默认实现：不支持。
        """
        raise NotImplementedError("copy_object is not implemented for this adapter")

    async def get_object_stream(
        self,
        locator: StorageLocator,
        *,
        chunk_size: int = 1024 * 1024,
        **kwargs
    ) -> Tuple[ObjectMetadata, AsyncIterator[bytes]]:
        """以流式方式读取对象内容。

        默认实现抛出未实现错误，具体适配器可覆盖以提供高效下载。
        
        Args:
            locator: 存储位置定位器
            chunk_size: 分块大小
            **kwargs: 额外参数，如 skip_exists_check (bool) 是否跳过存在性检查以提升性能
        """
        raise NotImplementedError("get_object_stream is not implemented for this adapter")


class StorageError(Exception):
    """存储操作的基础异常（领域层抽象）。"""

    def __init__(
        self,
        message: str,
        *,
        locator: Optional[StorageLocator] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.locator = locator
        self.cause = cause


class ObjectNotFoundError(StorageError):
    """当对象在存储中未找到时抛出的异常。"""

    pass


class ObjectAlreadyExistsError(StorageError):
    """当尝试创建已存在的对象时抛出的异常。"""

    pass


class StorageQuotaExceededError(StorageError):
    """当存储配额超出时抛出的异常。"""

    pass


class InvalidStorageLocationError(StorageError):
    """当存储位置无效时抛出的异常。"""

    pass


