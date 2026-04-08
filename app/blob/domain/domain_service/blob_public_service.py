from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from pydantic import BaseModel, Field


class BlobFileInfo(BaseModel):
    """仅包含文件相关的逻辑信息（不包含任何存储细节，如 locator/etag 等）。"""

    blob_id: str
    kind: str | None = None
    blob_sha256: str | None = None
    size_bytes: int
    mime_type: str | None = None
    display_name: str | None = None
    status: str | None = None
    created_at: str | None = None


class BlobDownloadSignature(BaseModel):
    """下载签名信息（由 blob 域签发/校验，不包含 user）。"""

    blob_id: str
    exp: int = Field(..., description="过期时间戳（秒）")
    nonce: str
    sig: str
    alg: str = Field(default="HMAC-SHA256")


class BlobPublicDomainService(ABC):
    """Blob 对外（给其他域/外部系统）的领域服务：只暴露“存与取”。"""

    @abstractmethod
    async def get_blob_info(self, *, blob_id: str) -> BlobFileInfo | None:
        """获取文件逻辑信息（不含存储细节）。"""

    @abstractmethod
    async def open_stream(
        self,
        *,
        blob_id: str,
        chunk_size: int = 1024 * 1024,
    ) -> tuple[BlobFileInfo, AsyncIterator[bytes]]:
        """打开文件流（内部使用存储定位器，但不对外暴露）。"""

    @abstractmethod
    async def create_download_url(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
        skip_exists_check: bool = False,
    ) -> str | None:
        """生成可直接访问的下载 URL（预签名/直链）。"""

    @abstractmethod
    async def create_download_signature(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
    ) -> BlobDownloadSignature:
        """生成下载签名信息。"""

    @abstractmethod
    def verify_download_signature(self, *, signature: BlobDownloadSignature) -> str:
        """校验下载签名，返回 blob_id（校验失败抛异常）。"""

