from __future__ import annotations

from typing import Optional, BinaryIO, Tuple
from uuid import uuid4
from datetime import datetime, timezone

from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.domain_service.file_processor import FileProcessorService
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.mime_type import MimeType
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.vo.blob_kind import BlobKind


class BlobFactory:
    """Blob 聚合根工厂。

    约束：Blob 与文件 1:1，创建必须基于文件流。
    工厂负责编排技术细节：文件处理、哈希计算、存储上传等。
    """

    def __init__(
        self,
        *,
        file_processor: FileProcessorService,
    ):
        """初始化工厂。

        工厂只依赖领域层的文件处理服务，不再直接依赖存储适配器，
        存储上传与元数据回填由应用服务或专门的领域服务负责。
        """
        self.file_processor = file_processor

    def _build_storage_locator(
        self,
        *,
        storage_provider: str,
        default_bucket: str,
        kind: BlobKind,
        region: Optional[str] = None,
    ) -> StorageLocator:
        """根据策略生成存储定位器。
        
        策略：
        - permanent：uploads/{yyyy}/{mm}/{dd}/{uuid}
        - temporary：tmp/uploads/{yyyy}/{mm}/{dd}/{uuid}
        """
        now = datetime.now(timezone.utc)
        prefix = "uploads"
        if kind == BlobKind.TEMPORARY:
            prefix = "tmp/uploads"
        object_key = f"{prefix}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{uuid4().hex}"
        # 生成 UUID hex 作为 storage_locator_id
        return StorageLocator(
            storage_locator_id=uuid4().hex,
            storage_provider=storage_provider,
            bucket=default_bucket,
            object_key=object_key,
            region=region,
        )

    def build_storage_locator(
        self,
        *,
        storage_provider: str,
        default_bucket: str,
        kind: BlobKind,
        region: Optional[str] = None,
    ) -> StorageLocator:
        """对外暴露的 locator 生成能力（用于 promote 等无需文件流的场景）。"""
        return self._build_storage_locator(
            storage_provider=storage_provider,
            default_bucket=default_bucket,
            kind=kind,
            region=region,
        )

    async def create_from_stream(
        self,
        *,
        fileobj: BinaryIO,
        content_type: Optional[str],
        storage_provider: str,
        default_bucket: str,
        kind: BlobKind = BlobKind.TEMPORARY,
        region: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Tuple[Blob, str, int]:
        """从文件流创建 Blob（仅负责领域对象构造与哈希计算）。

        注意：本方法不再负责上传到对象存储，也不回填存储元数据，
        只生成 `Blob` 聚合和对应的 `StorageLocator`，并计算内容哈希和大小。

        存储上传与元数据回填应由应用服务或基础设施领域服务完成。
        """
        # 1. 计算哈希和大小（纯领域逻辑）
        sha256_hex, size_bytes = await self.file_processor.compute_hash_and_size(fileobj)

        # 2. 生成存储定位（对象键策略仍由域内统一管理）
        locator = self._build_storage_locator(
            storage_provider=storage_provider,
            default_bucket=default_bucket,
            kind=kind,
            region=region,
        )

        # 3. 创建聚合根（尚未上传到存储，部分存储元数据为空）
        blob = Blob.create(
            blob_id=uuid4().hex,
            blob_sha256=SHA256Hash(value=sha256_hex),
            kind=kind,
            size_bytes=size_bytes,
            mime_type=MimeType(value=content_type) if content_type else None,
            storage_locator=locator,
            display_name=display_name,
        )

        # 4. 返回领域对象及哈希/大小信息，供上层完成上传和元数据回填
        return blob, sha256_hex, size_bytes
    
    def create_pending(
        self,
        *,
        blob_id: str,
        size_bytes: int,
        kind: BlobKind = BlobKind.TEMPORARY,
        mime_type: Optional[str] = None,
    ) -> Blob:
        """立即创建 pending 状态的 Blob（不进行 hash256 计算和存储上传）。
        
        Args:
            blob_id: Blob 标识符
            size_bytes: 文件大小
            mime_type: MIME 类型（可选）
            
        Returns:
            新创建的 pending 状态 Blob 聚合根
        """
        return Blob.create_pending(
            blob_id=blob_id,
            size_bytes=size_bytes,
            kind=kind,
            mime_type=MimeType(value=mime_type) if mime_type else None,
        )


