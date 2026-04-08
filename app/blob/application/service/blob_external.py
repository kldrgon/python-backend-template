from __future__ import annotations

from typing import AsyncIterator, Optional

from app.blob.domain.domain_service.blob_public_service import (
    BlobPublicDomainService,
    BlobDownloadSignature,
    BlobFileInfo,
)
from app.blob.domain.domain_service.blob_file_domain_service import BlobFileDomainService
from app.blob.domain.domain_service.blob_attachment_service import BlobAttachmentDomainService
from app.blob.domain.usecase.blob_external import BlobExternalUseCase
from app.blob.domain.vo.blob_kind import BlobKind
from pami_event_framework import Transactional


class BlobExternalCommandService(BlobExternalUseCase):
    """给外部系统用的 Command Service：临时上传（可携带 owner 信息）+ 签名下载。"""

    def __init__(
        self,
        *,
        blob_file_domain_service: BlobFileDomainService,
        blob_attachment_domain_service: BlobAttachmentDomainService,
        public_domain_service: BlobPublicDomainService,
    ) -> None:
        self._file_svc = blob_file_domain_service
        self._attach_svc = blob_attachment_domain_service
        self._public = public_domain_service

    @Transactional()
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
        """
        上传临时文件并返回 blob_id。

        若提供完整的 owner_type / owner_id / edge_key，则同时建立引用关系，
        使该 blob 在 GC 时被保护（不会被当作孤儿回收）。
        """
        if hasattr(fileobj, "seek"):
            fileobj.seek(0)

        blob = await self._file_svc.create_blob_from_stream(
            fileobj=fileobj,
            content_type=content_type,
            kind=BlobKind.TEMPORARY,
            display_name=display_name,
        )

        if owner_type and owner_id and edge_key:
            await self._attach_svc.attach(
                blob_id=blob.blob_id,
                owner_type=owner_type,
                owner_id=owner_id,
                edge_key=edge_key,
            )

        return blob.blob_id

    async def get_download_url(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
    ) -> str | None:
        return await self._public.create_download_url(
            blob_id=blob_id,
            expires_in_seconds=expires_in_seconds,
        )

    async def get_download_signature(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
    ) -> BlobDownloadSignature:
        return await self._public.create_download_signature(
            blob_id=blob_id,
            expires_in_seconds=expires_in_seconds,
        )

    async def download_by_signature(
        self,
        *,
        signature: BlobDownloadSignature,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        blob_id = self._public.verify_download_signature(signature=signature)
        _info, iterator = await self._public.open_stream(blob_id=blob_id, chunk_size=chunk_size)
        return iterator
