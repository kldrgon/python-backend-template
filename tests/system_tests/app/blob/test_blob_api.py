"""Blob API system tests.

Routes under test: /blob/v1/upload, /blob/v1/download
Storage layer is replaced with LocalStorageAdapter to avoid real MinIO/S3.
"""

import io
import pytest_asyncio
from dependency_injector import providers as di_providers

from app.blob.adapter.output.storage.local_storage_adapter import LocalStorageAdapter


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def local_storage(app, tmp_path_factory):
    """
    override BlobContainer 的 storage_adapter，
    让 Blob 测试使用 LocalStorageAdapter 替代 MinIO/S3。
    同时 reset 依赖 storage_adapter 的 Singleton，使其用新 adapter 重建。
    """
    base = tmp_path_factory.mktemp("blob_storage")
    adapter = LocalStorageAdapter(base_path=str(base))
    blob = app.container.blob_container
    blob.storage_adapter.override(di_providers.Object(adapter))
    blob.blob_public_domain_service.reset()
    blob.blob_file_domain_service.reset()
    blob.thumbnail_cache_adapter.reset()
    yield adapter
    blob.storage_adapter.reset_override()
    blob.blob_public_domain_service.reset()
    blob.blob_file_domain_service.reset()
    blob.thumbnail_cache_adapter.reset()


class TestUploadApi:

    async def test_upload_returns_blob_id(self, client, auth_headers):
        content = b"hello blob"
        resp = await client.post(
            "/blob/v1/upload",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "blob_id" in data
        assert isinstance(data["blob_id"], str)

    async def test_upload_with_owner_info(self, client, auth_headers, registered_user):
        content = b"avatar content"
        resp = await client.post(
            "/blob/v1/upload",
            files={"file": ("avatar.jpg", io.BytesIO(content), "image/jpeg")},
            params={
                "owner_type": "user",
                "owner_id": registered_user["user_id"],
                "edge_key": "avatar",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "blob_id" in data

    async def test_upload_without_auth_returns_401(self, client):
        resp = await client.post(
            "/blob/v1/upload",
            files={"file": ("test.txt", io.BytesIO(b"data"), "text/plain")},
        )
        assert resp.status_code == 401

    async def test_upload_returns_download_url(self, client, auth_headers):
        content = b"file content"
        resp = await client.post(
            "/blob/v1/upload",
            files={"file": ("doc.txt", io.BytesIO(content), "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "download_url" in data


class TestDownloadApi:

    async def _upload_and_get_url(self, client, auth_headers, content: bytes = b"test"):
        resp = await client.post(
            "/blob/v1/upload",
            files={"file": ("file.bin", io.BytesIO(content), "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        return resp.json()["data"].get("download_url")

    async def test_download_valid_signature(self, client, auth_headers):
        content = b"download me"
        download_url = await self._upload_and_get_url(client, auth_headers, content)
        assert download_url is not None

        path_and_query = download_url.split("/blob/v1/", 1)[1]
        resp = await client.get(f"/blob/v1/{path_and_query}")

        assert resp.status_code == 200
        assert resp.content == content

    async def test_download_invalid_signature_returns_403(self, client):
        resp = await client.get(
            "/blob/v1/download",
            params={"blob_id": "fakeid", "exp": 9999999999, "nonce": "abc", "sig": "invalidsig"},
        )
        assert resp.status_code == 403

    async def test_download_expired_signature_returns_403(self, client, auth_headers):
        content = b"expiry test"
        resp = await client.post(
            "/blob/v1/upload",
            files={"file": ("expire.bin", io.BytesIO(content), "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        blob_id = resp.json()["data"]["blob_id"]

        resp = await client.get(
            "/blob/v1/download",
            params={"blob_id": blob_id, "exp": 1, "nonce": "nonce", "sig": "badsig"},
        )
        assert resp.status_code == 403

    async def test_download_response_headers(self, client, auth_headers):
        content = b"header check"
        download_url = await self._upload_and_get_url(client, auth_headers, content)
        assert download_url is not None

        path_and_query = download_url.split("/blob/v1/", 1)[1]
        resp = await client.get(f"/blob/v1/{path_and_query}")

        assert resp.status_code == 200
        assert "content-length" in resp.headers
        assert int(resp.headers["content-length"]) == len(content)
