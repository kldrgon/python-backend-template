from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.vo.blob_kind import BlobKind


class BlobFileDomainService(ABC):
    """统一的文件→Blob 领域服务接口。

    封装哈希去重、Blob 聚合构造、对象存储上传与存储元数据回填，
    对外只暴露“基于文件流创建或复用 Blob”这一能力，不关心业务主体。
    """

    @abstractmethod
    async def create_blob_from_stream(
        self,
        *,
        fileobj: BinaryIO,
        content_type: Optional[str],
        kind: BlobKind = BlobKind.PERMANENT,
        display_name: Optional[str] = None,
    ) -> Blob:
        """从文件流创建 Blob。
        - 创建新的 Blob 记录并上传到对象存储。默认持久化
        """
        ...

    @abstractmethod
    async def promote_temp_to_permanent(self, *, blob_id: str) -> Blob | None:
        """
        将 temporary Blob 固化为 permanent：
        - 更新 storage_locator（tmp/uploads -> uploads）
        - 更新 kind
        - 存储层优先 CopyObject；不支持则降级下载+上传
        - 成功后立即删除旧对象
        """
        ...


