from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import AsyncIterator, Optional

from app.blob.domain.domain_service.blob_public_service import (
    BlobPublicDomainService,
    BlobFileInfo,
    BlobDownloadSignature,
)
from app.blob.domain.repository.blob import BlobRepository
from app.blob.domain.domain_service.storage_adapter import StorageAdapter
from app.blob.domain.vo.blob_status import BlobStatus
from core.config import config


class InvalidBlobDownloadSignatureError(ValueError):
    pass


class ExpiredBlobDownloadSignatureError(ValueError):
    pass


class SQLAlchemyBlobPublicDomainService(BlobPublicDomainService):
    def __init__(
        self,
        *,
        repository: BlobRepository,
        storage_adapter: StorageAdapter,
        signing_secret: str | None = None,
    ) -> None:
        self._repo = repository
        self._storage = storage_adapter
        self._secret = (signing_secret or config.blob_storage.signing_secret_key or config.jwt.secret_key).encode(
            "utf-8"
        )

    async def get_blob_info(self, *, blob_id: str) -> BlobFileInfo | None:
        blob = await self._repo.get_by_id(blob_id=blob_id)
        if blob is None:
            return None
        return BlobFileInfo(
            blob_id=blob.blob_id,
            kind=getattr(blob, "kind", None).value if getattr(blob, "kind", None) else None,
            blob_sha256=str(blob.blob_sha256) if blob.blob_sha256 else None,
            size_bytes=blob.size_bytes,
            mime_type=str(blob.mime_type) if blob.mime_type else None,
            display_name=blob.display_name,
            status=blob.status.value if blob.status else None,
            created_at=blob.created_at.isoformat() if blob.created_at else None,
        )

    async def open_stream(
        self,
        *,
        blob_id: str,
        chunk_size: int = 1024 * 1024,
    ) -> tuple[BlobFileInfo, AsyncIterator[bytes]]:
        blob = await self._repo.get_by_id(blob_id=blob_id)
        if blob is None:
            raise ValueError("Blob not found")
        if blob.status != BlobStatus.READY:
            raise ValueError("Blob not ready")
        if not blob.storage_locator:
            raise ValueError("Blob storage location missing")

        info = await self.get_blob_info(blob_id=blob_id)
        assert info is not None

        _meta, iterator = await self._storage.get_object_stream(
            blob.storage_locator,
            chunk_size=chunk_size,
            skip_exists_check=True,
        )
        return info, iterator

    async def create_download_url(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
        skip_exists_check: bool = False,
    ) -> str | None:
        blob = await self._repo.get_by_id(blob_id=blob_id)
        if blob is None:
            return None
        if blob.status != BlobStatus.READY:
            raise ValueError("Blob not ready")
        if not blob.storage_locator:
            raise ValueError("Blob storage location missing")
        default_expires = getattr(config, "BLOB_URL_EXPIRES", 3600)
        return await self._storage.get_object_url(
            blob.storage_locator,
            expires_in_seconds=expires_in_seconds or default_expires,
            skip_exists_check=skip_exists_check,
        )

    async def create_download_signature(
        self,
        *,
        blob_id: str,
        expires_in_seconds: Optional[int] = None,
    ) -> BlobDownloadSignature:
        blob = await self._repo.get_by_id(blob_id=blob_id)
        if blob is None:
            raise ValueError("Blob not found")
        if blob.status != BlobStatus.READY:
            raise ValueError("Blob not ready")

        ttl = int(expires_in_seconds or getattr(config, "BLOB_URL_EXPIRES", 3600))
        ttl = max(1, min(ttl, 7 * 24 * 3600))
        now = int(time.time())
        exp = ((now // ttl) + 1) * ttl
        nonce = hashlib.sha256(f"{blob_id}:{exp}".encode("utf-8")).hexdigest()[:16]
        sig = self._sign(blob_id=blob_id, exp=exp, nonce=nonce)
        return BlobDownloadSignature(blob_id=blob_id, exp=exp, nonce=nonce, sig=sig)

    def verify_download_signature(self, *, signature: BlobDownloadSignature) -> str:
        now = int(time.time())
        if signature.exp < now:
            raise ExpiredBlobDownloadSignatureError("signature expired")
        expected = self._sign(blob_id=signature.blob_id, exp=signature.exp, nonce=signature.nonce)
        if not hmac.compare_digest(expected, signature.sig):
            raise InvalidBlobDownloadSignatureError("invalid signature")
        return signature.blob_id

    def _sign(self, *, blob_id: str, exp: int, nonce: str) -> str:
        msg = f"{blob_id}:{exp}:{nonce}".encode("utf-8")
        digest = hmac.new(self._secret, msg, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
