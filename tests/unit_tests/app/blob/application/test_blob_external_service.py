"""BlobExternalCommandService 单元测试

覆盖：
- upload_temp()：无 owner 信息时只调用 create_blob_from_stream
- upload_temp()：有完整 owner 信息时额外调用 attach
- upload_temp()：owner 信息不完整时不调用 attach
- upload_temp()：返回 blob_id
- get_download_url()：委托给 public_domain_service
- get_download_signature()：委托给 public_domain_service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.blob.application.service.blob_external import BlobExternalCommandService
from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.vo.blob_status import BlobStatus
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.entity.storage_locator import StorageLocator


VALID_SHA256 = "a" * 64


def _make_blob(blob_id: str = "blob-001") -> Blob:
    return Blob.create(
        blob_id=blob_id,
        blob_sha256=SHA256Hash(value=VALID_SHA256),
        size_bytes=512,
        mime_type=None,
        storage_locator=StorageLocator(
            storage_provider="minio",
            bucket="test-bucket",
            object_key="uploads/file.bin",
        ),
    )


def _make_service(
    blob: Blob | None = None,
) -> tuple[BlobExternalCommandService, AsyncMock, AsyncMock, AsyncMock]:
    """返回 (service, file_svc_mock, attach_svc_mock, public_svc_mock)"""
    if blob is None:
        blob = _make_blob()

    file_svc = AsyncMock()
    file_svc.create_blob_from_stream = AsyncMock(return_value=blob)

    attach_svc = AsyncMock()
    attach_svc.attach = AsyncMock()

    public_svc = AsyncMock()

    svc = BlobExternalCommandService(
        blob_file_domain_service=file_svc,
        blob_attachment_domain_service=attach_svc,
        public_domain_service=public_svc,
    )
    return svc, file_svc, attach_svc, public_svc


class TestUploadTemp:
    @pytest.mark.asyncio
    async def test_returns_blob_id(self):
        svc, _, _, _ = _make_service(_make_blob("my-blob-id"))
        result = await svc.upload_temp(fileobj=MagicMock())
        assert result == "my-blob-id"

    @pytest.mark.asyncio
    async def test_calls_create_blob_from_stream(self):
        svc, file_svc, _, _ = _make_service()
        await svc.upload_temp(fileobj=MagicMock(), content_type="image/png")
        file_svc.create_blob_from_stream.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_attach_when_owner_info_absent(self):
        svc, _, attach_svc, _ = _make_service()
        await svc.upload_temp(fileobj=MagicMock())
        attach_svc.attach.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_attaches_when_owner_info_complete(self):
        svc, _, attach_svc, _ = _make_service()
        await svc.upload_temp(
            fileobj=MagicMock(),
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )
        attach_svc.attach.assert_awaited_once_with(
            blob_id="blob-001",
            owner_type="user",
            owner_id="user-001",
            edge_key="avatar",
        )

    @pytest.mark.asyncio
    async def test_no_attach_when_owner_id_missing(self):
        svc, _, attach_svc, _ = _make_service()
        await svc.upload_temp(
            fileobj=MagicMock(),
            owner_type="user",
            owner_id=None,
            edge_key="avatar",
        )
        attach_svc.attach.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_attach_when_edge_key_missing(self):
        svc, _, attach_svc, _ = _make_service()
        await svc.upload_temp(
            fileobj=MagicMock(),
            owner_type="user",
            owner_id="user-001",
            edge_key=None,
        )
        attach_svc.attach.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_seekable_fileobj_is_seeked(self):
        svc, _, _, _ = _make_service()
        mock_file = MagicMock()
        mock_file.seek = MagicMock()
        await svc.upload_temp(fileobj=mock_file)
        mock_file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_non_seekable_fileobj_not_seeked(self):
        svc, _, _, _ = _make_service()
        # 模拟没有 seek 属性的对象
        mock_file = MagicMock(spec=[])
        # 不应抛出异常
        await svc.upload_temp(fileobj=mock_file)


class TestGetDownloadUrl:
    @pytest.mark.asyncio
    async def test_delegates_to_public_service(self):
        svc, _, _, public_svc = _make_service()
        public_svc.create_download_url = AsyncMock(return_value="https://example.com/dl")
        result = await svc.get_download_url(blob_id="blob-001")
        public_svc.create_download_url.assert_awaited_once_with(
            blob_id="blob-001",
            expires_in_seconds=None,
        )
        assert result == "https://example.com/dl"

    @pytest.mark.asyncio
    async def test_passes_expires_in_seconds(self):
        svc, _, _, public_svc = _make_service()
        public_svc.create_download_url = AsyncMock(return_value="https://example.com/dl")
        await svc.get_download_url(blob_id="blob-001", expires_in_seconds=300)
        call_kwargs = public_svc.create_download_url.call_args.kwargs
        assert call_kwargs["expires_in_seconds"] == 300


class TestGetDownloadSignature:
    @pytest.mark.asyncio
    async def test_delegates_to_public_service(self):
        svc, _, _, public_svc = _make_service()
        mock_sig = MagicMock()
        public_svc.create_download_signature = AsyncMock(return_value=mock_sig)
        result = await svc.get_download_signature(blob_id="blob-001")
        public_svc.create_download_signature.assert_awaited_once_with(
            blob_id="blob-001",
            expires_in_seconds=None,
        )
        assert result is mock_sig
