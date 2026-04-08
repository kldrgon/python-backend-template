"""兼容旧路径的适配层。

存储抽象已迁移到领域层 `app.blob.domain.domain_service.storage_adapter`，
此模块仅保留以兼容历史导入路径。
"""

from app.blob.domain.domain_service.storage_adapter import (  # noqa: F401
    StorageAdapter,
    ObjectMetadata,
    StorageError,
    ObjectNotFoundError,
    ObjectAlreadyExistsError,
    StorageQuotaExceededError,
    InvalidStorageLocationError,
)
