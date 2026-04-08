from app.blob.adapter.output.storage import create_storage_adapter
from app.blob.adapter.output.storage.local_storage_adapter import LocalStorageAdapter
from core.config import config


def test_create_storage_adapter_returns_local_adapter(tmp_path):
    old_provider = config.blob_storage.storage_provider
    old_base_path = config.blob_storage.local_base_path
    try:
        config.blob_storage.storage_provider = "local"
        config.blob_storage.local_base_path = str(tmp_path)

        adapter = create_storage_adapter()

        assert isinstance(adapter, LocalStorageAdapter)
        assert adapter.base_path == tmp_path
    finally:
        config.blob_storage.storage_provider = old_provider
        config.blob_storage.local_base_path = old_base_path
