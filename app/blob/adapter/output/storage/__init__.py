from app.blob.domain.domain_service.storage_adapter import StorageAdapter, ObjectMetadata, StorageError
from .local_storage_adapter import LocalStorageAdapter
from .s3_storage_adapter import S3StorageAdapter
from .minio_storage_adapter import MinIOStorageAdapter
from core.config import config


def create_storage_adapter() -> StorageAdapter:
    provider = config.blob_storage.storage_provider.lower()

    print(f"[Storage] Provider: {provider}")
    print(f"[Storage] disable_chunked_encoding: {config.blob_storage.disable_chunked_encoding}")
    print(f"[Storage] endpoint: {config.blob_storage.endpoint}")
    print(f"[Storage] region: {config.blob_storage.region}")

    if provider == "local":
        return LocalStorageAdapter(
            base_path=config.blob_storage.local_base_path,
        )
    elif provider == "minio":
        return MinIOStorageAdapter(
            endpoint=config.blob_storage.endpoint,
            access_key=config.blob_storage.access_key,
            secret_key=config.blob_storage.secret_key,
            secure=config.blob_storage.is_secure,
            region=config.blob_storage.region,
            disable_chunked_encoding=config.blob_storage.disable_chunked_encoding,
        )
    elif provider in ("s3", "aliyun_oss"):
        endpoint_url = f"{'https' if config.blob_storage.is_secure else 'http'}://{config.blob_storage.endpoint}"
        return S3StorageAdapter(
            aws_access_key_id=config.blob_storage.access_key,
            aws_secret_access_key=config.blob_storage.secret_key,
            region_name=config.blob_storage.region,
            endpoint_url=endpoint_url,
            disable_chunked_encoding=config.blob_storage.disable_chunked_encoding,
        )
    else:
        raise ValueError(f"不支持的存储提供商: {provider}")


__all__ = [
    "StorageAdapter",
    "ObjectMetadata",
    "StorageError",
    "LocalStorageAdapter",
    "S3StorageAdapter",
    "MinIOStorageAdapter",
    "create_storage_adapter",
]