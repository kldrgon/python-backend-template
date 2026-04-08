from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from app.blob.domain.domain_service.blob_public_service import (
    BlobDownloadSignature,
)


class BlobExternalUseCase(ABC):
    """Blob 对外的用例接口：临时上传、签名下载、流式下载。"""

    @abstractmethod
    async def upload_temp(
        self,
        *,
        fileobj,
        content_type: Optional[str] = None,
        display_name: Optional[str] = None,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        edge_key: Optional[str] = None,
    ) -> str:
        """上传临时文件，返回 blob_id。可选携带 owner 信息建立引用。"""

    @abstractmethod
    async def get_download_url(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
    ) -> str | None:
        """生成可直接访问的下载 URL。"""

    @abstractmethod
    async def get_download_signature(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
    ) -> BlobDownloadSignature:
        """生成下载签名。"""

    @abstractmethod
    async def download_by_signature(
        self,
        *,
        signature: BlobDownloadSignature,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        """通过签名获取文件字节流。"""
