from __future__ import annotations

from abc import ABC, abstractmethod

from app.blob.domain.aggregate.blob_reference import BlobReference


class BlobReferenceRepository(ABC):
    """BlobReference 聚合根的仓储接口。"""

    @abstractmethod
    async def save(self, *, ref: BlobReference) -> None:
        """
        保存引用（upsert）。
        同一 owner_type + owner_id + edge_key 的引用若已存在则覆盖。
        """
        ...

    @abstractmethod
    async def delete_by_edge(
        self,
        *,
        owner_type: str,
        owner_id: str,
        edge_key: str,
    ) -> bool:
        """
        删除指定主体的某条引用。

        Returns:
            删除成功返回 True，记录不存在返回 False
        """
        ...

    @abstractmethod
    async def delete_all_by_owner(
        self,
        *,
        owner_type: str,
        owner_id: str,
    ) -> int:
        """
        删除指定主体的所有引用（主体删除时调用）。

        Returns:
            实际删除的行数
        """
        ...
