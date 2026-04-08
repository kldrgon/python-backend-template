from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app.blob.domain.aggregate.blob import Blob


class BlobRepository(ABC):
    """Blob 聚合的仓储接口。"""
    
    @abstractmethod
    async def get_by_id(self, *, blob_id: str) -> Optional[Blob]:
        """
        通过 ID 获取 Blob。
        
        Args:
            blob_id: Blob 标识符
            
        Returns:
            若找到返回 Blob，否则返回 None
        """
        ...

    @abstractmethod
    async def get_by_hash(self, *, blob_sha256: str) -> Optional[Blob]:
        """
        通过 SHA256 哈希获取 Blob（返回第一个有 storage_locator 的 Blob，用于去重）。
        
        Args:
            blob_sha256: SHA256 哈希值
            
        Returns:
            若找到返回 Blob，否则返回 None
        """
        ...
    
    @abstractmethod
    async def list_by_hash(self, *, blob_sha256: str) -> List[Blob]:
        """
        通过 SHA256 哈希获取所有 Blob（用于查询 ref）。
        
        Args:
            blob_sha256: SHA256 哈希值
            
        Returns:
            匹配的 Blob 列表
        """
        ...

    @abstractmethod
    async def exists_by_hash(self, *, blob_sha256: str) -> bool:
        """
        通过 SHA256 哈希判断 Blob 是否存在。
        
        Args:
            blob_sha256: SHA256 哈希值
            
        Returns:
            若存在返回 True，否则返回 False
        """
        ...

    @abstractmethod
    async def exists_by_storage_key(self, *, storage_unique_key: str) -> bool:
        """
        通过存储唯一键判断 Blob 是否存在。
        
        Args:
            storage_unique_key: 存储位置的唯一键
            
        Returns:
            若存在返回 True，否则返回 False
        """
        ...

    @abstractmethod
    async def get_by_storage_locator(
        self, 
        *, 
        storage_provider: str, 
        bucket: str, 
        object_key: str
    ) -> Optional[Blob]:
        """
        通过存储定位器查找 Blob。
        
        Args:
            storage_provider: 存储提供商
            bucket: 存储桶
            object_key: 对象键
            
        Returns:
            若找到返回 Blob，否则返回 None
        """
        ...

    @abstractmethod
    async def save(self, *, blob: Blob) -> None:
        """
        保存 Blob 聚合。
        
        Args:
            blob: 需要保存的 Blob 聚合
        """
        ...

    @abstractmethod
    async def delete(self, *, blob_id: str) -> bool:
        """
        通过 ID 删除 Blob。
        
        Args:
            blob_id: Blob 标识符
            
        Returns:
            删除成功返回 True，未找到返回 False
        """
        ...



