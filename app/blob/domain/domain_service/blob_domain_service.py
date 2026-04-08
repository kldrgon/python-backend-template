from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.entity.storage_locator import StorageLocator


class BlobDomainService(ABC):
    """Blob 领域服务接口。
    
    用于：
    1. 跨聚合的业务逻辑（如获取存储位置信息供其他上下文使用）
    2. 本聚合内不适合放在 Repository 和聚合根中的复杂业务逻辑（如 GC 候选查找）
    """
    
    @abstractmethod
    async def has_blob(self, *, blob_id: str) -> bool:
        """判断指定 blob 是否存在。"""
        ...

    @abstractmethod
    async def find_gc_candidates(
        self, 
        *, 
        limit: Optional[int] = None, 
        older_than: Optional[datetime] = None
    ) -> List[Blob]:
        """查找符合垃圾回收条件的 Blob。
        
        业务规则：只返回 temporary Blob（临时对象），供垃圾回收处理。
        这个方法包含业务逻辑判断，不适合放在 Repository 或聚合根中。
        
        Args:
            limit: 返回候选数量上限
            older_than: 仅返回创建时间早于该时间点的 Blob
            
        Returns:
            垃圾回收候选 Blob 列表
        """
        ...
    
    @abstractmethod
    async def get_storage_locator_by_hash(self, *, sha256: str) -> Optional[StorageLocator]:
        """通过 SHA256 哈希查找 StorageLocator。
        
        返回第一个匹配的 StorageLocator（按创建时间降序）。
        备注：历史上用于去重定位；当前写入链路不再复用，但该查询仍可用于排查/分析。
        
        Args:
            sha256: SHA256 哈希值
            
        Returns:
            如果找到返回 StorageLocator，否则返回 None
        """
        ...
    
    @abstractmethod
    async def get_storage_locator(self, *, blob_id: str) -> Optional[StorageLocator]:
        """返回指定 blob 的存储定位（StorageLocator）或 None。
        
        用于跨上下文获取存储位置信息。
        """
        ...

    @abstractmethod
    async def find_unreferenced_permanent_candidates(
        self,
        *,
        limit: Optional[int] = None,
    ) -> List[Blob]:
        """查找无引用的 PERMANENT Blob（GC 候选）。

        业务规则：PERMANENT Blob 若在 blob_reference 表中无任何引用行，
        说明所有持有方均已解绑，文件可安全回收。

        Args:
            limit: 返回候选数量上限

        Returns:
            无引用的 PERMANENT Blob 列表
        """
        ...


