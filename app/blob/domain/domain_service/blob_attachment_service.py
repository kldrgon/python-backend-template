from __future__ import annotations

from abc import ABC, abstractmethod


class BlobAttachmentDomainService(ABC):
    """
    Blob 引用管理领域服务（blob 域内部服务）。

    负责维护 BlobReference 聚合的生命周期：建立引用、解除引用。
    由 BlobExternalCommandService 在上传时调用，不作为跨上下文接口对外暴露。
    跨上下文的解绑（如主体删除）通过领域事件驱动，事件处理器调用 detach_all。
    """

    @abstractmethod
    async def attach(
        self,
        *,
        blob_id: str,
        owner_type: str,
        owner_id: str,
        edge_key: str,
    ) -> None:
        """
        建立引用关系（upsert）。
        同一 owner_type + owner_id + edge_key 若已有引用，则更新指向新 blob_id。
        """
        ...

    @abstractmethod
    async def detach(
        self,
        *,
        owner_type: str,
        owner_id: str,
        edge_key: str,
    ) -> bool:
        """
        解除单条引用。

        Returns:
            成功删除返回 True，记录不存在返回 False
        """
        ...

    @abstractmethod
    async def detach_all(
        self,
        *,
        owner_type: str,
        owner_id: str,
    ) -> int:
        """
        解除指定主体的所有引用（主体删除时调用）。

        Returns:
            实际删除的引用数量
        """
        ...
