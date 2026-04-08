from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, field_validator
from typing import Optional
from datetime import datetime

from pami_event_framework import AggregateRoot
from app.blob.domain.event.blob_events import (
    BlobCreatedEvent,
    BlobProcessingStartedEvent,
    BlobProcessingCompletedEvent,
    BlobProcessingFailedEvent,
    BlobDeletedEvent,
    BlobGcRequestedEvent,
)
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.vo.mime_type import MimeType
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.etag import Etag
from app.blob.domain.vo.blob_status import BlobStatus
from app.blob.domain.vo.blob_kind import BlobKind
from app.blob.domain.exception.errors import InvalidBlobStatusError


class Blob(AggregateRoot, BaseModel):
    """
    面向内容寻址存储的 Blob 聚合根。
    
    使用 `blob_id` 作为跨上下文的引用标识，使用 `blob_sha256` 进行去重与完整性校验，
    为内容寻址存储提供统一抽象。
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    # 身份标识
    blob_id: str = Field(..., description="跨上下文引用标识符")
    blob_sha256: Optional[SHA256Hash] = Field(None, description="用于去重与完整性校验的内容哈希值")
    kind: BlobKind = Field(default=BlobKind.TEMPORARY, description="Blob 类型：临时/永久")
    
    # 内容元数据
    size_bytes: int = Field(..., ge=0, description="内容大小（字节）")
    mime_type: Optional[MimeType] = Field(None, description="内容 MIME 类型")
    display_name: Optional[str] = Field(None, description="显示名称")
    
    # 存储位置
    storage_locator: Optional[StorageLocator] = Field(None, description="存储位置详情")
    etag: Optional[Etag] = Field(None, description="存储层用于版本控制的 ETag")
    storage_class: Optional[str] = Field(None, description="存储级别（如 STANDARD、IA、GLACIER 等）")
    
    # 处理状态
    status: BlobStatus = Field(default=BlobStatus.PENDING, description="Blob 处理状态")
    
    # 时间戳（由持久化层处理）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    _domain_events: list = PrivateAttr(default_factory=list)

    def __init__(self, **kwargs):
        """初始化 Blob 聚合根"""
        AggregateRoot.__init__(self)
        BaseModel.__init__(self, **kwargs)
    
    def get_aggregate_id(self) -> str:
        """实现 AggregateRoot 抽象方法：返回聚合根ID"""
        return self.blob_id
    
    @field_validator("blob_sha256", mode="before")
    @classmethod
    def validate_sha256_hash(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return SHA256Hash(value=v)
        return v
    
    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            return BlobStatus(v)
        return v

    @field_validator("kind", mode="before")
    @classmethod
    def validate_kind(cls, v):
        if isinstance(v, str):
            return BlobKind(v)
        return v
    
    @field_validator("mime_type", mode="before")
    @classmethod
    def validate_mime_type(cls, v):
        if isinstance(v, str) and v:
            return MimeType(value=v)
        return v
    
    @field_validator("etag", mode="before")
    @classmethod
    def validate_etag(cls, v):
        if isinstance(v, str) and v:
            return Etag(value=v)
        return v
    
    @classmethod
    def create(
        cls,
        *,
        blob_id: str,
        blob_sha256: SHA256Hash,
        kind: BlobKind = BlobKind.TEMPORARY,
        size_bytes: int,
        mime_type: Optional[MimeType],
        storage_locator: StorageLocator,
        etag: Optional[Etag] = None,
        storage_class: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> "Blob":
        """创建 Blob 聚合根（纯领域逻辑）。
        
        Args:
            blob_id: Blob 标识符
            blob_sha256: SHA256 哈希
            size_bytes: 文件大小
            mime_type: MIME 类型
            storage_locator: 存储定位器
            etag: ETag（可选）
            storage_class: 存储类别（可选）
            display_name: 显示名称（可选）
            
        Returns:
            新创建的 Blob 聚合根
        """
        blob = cls(
            blob_id=blob_id,
            blob_sha256=blob_sha256,
            kind=kind,
            size_bytes=size_bytes,
            mime_type=mime_type,
            storage_locator=storage_locator,
            etag=etag,
            storage_class=storage_class,
            status=BlobStatus.READY,
            display_name=display_name,
        )
        blob.raise_event(BlobCreatedEvent(
            blob_id=blob.blob_id,
            blob_sha256=str(blob_sha256),
            size_bytes=size_bytes,
            storage_provider=storage_locator.storage_provider,
            bucket=storage_locator.bucket,
            object_key=storage_locator.object_key,
            region=storage_locator.region,
        ))
        return blob
    
    @classmethod
    def create_pending(
        cls,
        *,
        blob_id: str,
        size_bytes: int,
        kind: BlobKind = BlobKind.TEMPORARY,
        mime_type: Optional[MimeType] = None,
        display_name: Optional[str] = None,
    ) -> "Blob":
        """创建 pending 状态的 Blob（立即返回，后台处理 hash256 和存储上传）。
        
        Args:
            blob_id: Blob 标识符
            size_bytes: 文件大小
            mime_type: MIME 类型（可选）
            display_name: 显示名称（可选）
            
        Returns:
            新创建的 pending 状态 Blob 聚合根
        """
        blob = cls(
            blob_id=blob_id,
            blob_sha256=None,
            kind=kind,
            size_bytes=size_bytes,
            mime_type=mime_type,
            storage_locator=None,
            status=BlobStatus.PENDING,
            display_name=display_name,
        )
        return blob

    def mark_processing(self) -> None:
        """标记 Blob 为处理中状态。"""
        if self.status != BlobStatus.PENDING:
            raise InvalidBlobStatusError(
                blob_id=self.blob_id,
                current_status=self.status,
                expected_status=BlobStatus.PENDING,
            )
        self.status = BlobStatus.PROCESSING
        self.raise_event(BlobProcessingStartedEvent(blob_id=self.blob_id))
    
    def mark_ready(
        self,
        *,
        blob_sha256: SHA256Hash,
        storage_locator: StorageLocator,
        etag: Optional[Etag] = None,
        storage_class: Optional[str] = None,
        owner_id: Optional[str] = None,
        owner_type: Optional[str] = None,
        edge_key: Optional[str] = None,
    ) -> None:
        """标记 Blob 为就绪状态，并更新 hash256 和存储位置。
        
        Args:
            blob_sha256: SHA256 哈希值
            storage_locator: 存储定位器
            etag: ETag（可选）
            storage_class: 存储类别（可选）
        """
        if self.status != BlobStatus.PROCESSING:
            raise InvalidBlobStatusError(
                blob_id=self.blob_id,
                current_status=self.status,
                expected_status=BlobStatus.PROCESSING,
            )
        self.status = BlobStatus.READY
        self.blob_sha256 = blob_sha256
        self.storage_locator = storage_locator
        if etag is not None:
            self.etag = etag
        if storage_class is not None:
            self.storage_class = storage_class
        self.raise_event(BlobProcessingCompletedEvent(
            blob_id=self.blob_id,
            blob_sha256=str(blob_sha256),
            storage_provider=storage_locator.storage_provider,
            bucket=storage_locator.bucket,
            object_key=storage_locator.object_key,
            region=storage_locator.region,
            owner_id=owner_id,
            owner_type=owner_type,
            edge_key=edge_key,
        ))
    
    def mark_failed(self, *, reason: str | None = None) -> None:
        """标记 Blob 为失败状态。
        
        Args:
            reason: 失败原因（可选）
        """
        self.status = BlobStatus.FAILED
        self.raise_event(BlobProcessingFailedEvent(
            blob_id=self.blob_id,
            reason=reason,
        ))
    
    def update_hash_and_storage(
        self,
        *,
        blob_sha256: SHA256Hash,
        storage_locator: StorageLocator,
        etag: Optional[Etag] = None,
        storage_class: Optional[str] = None,
    ) -> None:
        """更新 hash256 和存储位置（用于后台任务）。
        
        Args:
            blob_sha256: SHA256 哈希值
            storage_locator: 存储定位器
            etag: ETag（可选）
            storage_class: 存储类别（可选）
        """
        self.blob_sha256 = blob_sha256
        self.storage_locator = storage_locator
        if etag is not None:
            self.etag = etag
        if storage_class is not None:
            self.storage_class = storage_class

    def delete(self) -> None:
        """
        将该 Blob 标记为删除。
        """
        self.raise_event(BlobDeletedEvent(blob_id=self.blob_id))

    # GC 相关方法不对外暴露
    
    def update_storage_metadata(
        self, 
        *, 
        etag: Optional[str | Etag] = None,
        storage_class: Optional[str] = None
    ) -> None:
        """
        在存储操作后更新存储元数据。
        
        Args:
            etag: 存储系统返回的新 ETag
            storage_class: 新的存储级别
        """
        if etag is not None:
            self.etag = Etag(value=etag) if isinstance(etag, str) else etag
        if storage_class is not None:
            self.storage_class = storage_class
    
    def verify_integrity(self, *, content_sha256: str) -> bool:
        """
        根据已存哈希校验内容完整性。
        
        Args:
            content_sha256: 实际内容的 SHA256 哈希
            
        Returns:
            若匹配返回 True，否则返回 False
        """
        if self.blob_sha256 is None:
            return False
        return str(self.blob_sha256) == content_sha256.lower()
    
    @property
    def storage_unique_key(self) -> Optional[str]:
        """获取用于存储去重约束的唯一键。"""
        if not self.storage_locator:
            return None
        return self.storage_locator.unique_key
    
    @property
    def is_stored(self) -> bool:
        """检查该 Blob 是否已有存储位置信息。"""
        return self.storage_locator is not None
    
    def get_thumbnail_locator(self, max_bytes: int) -> Optional[StorageLocator]:
        """获取特定规格缩略图的存储定位器。
        
        由聚合根负责生成其衍生资源的定位信息，保证一致性和边界。
        
        Args:
            max_bytes: 缩略图最大字节数规格
            
        Returns:
            StorageLocator: 缩略图的存储定位器，如果原图未就绪返回 None
        """
        if not self.storage_locator:
            return None
            
        # 构造规则：cache/thumbnails/{blob_id}_{max_bytes}
        # 继承原图的 provider 和 bucket
        cache_key = f"cache/thumbnails/{self.blob_id}_{max_bytes}"
        
        return StorageLocator(
            storage_provider=self.storage_locator.storage_provider,
            bucket=self.storage_locator.bucket,
            object_key=cache_key,
            region=self.storage_locator.region
        )

    def __str__(self) -> str:
        return f"Blob(id={self.blob_id}, sha256={self.blob_sha256}, size={self.size_bytes}, status={self.status})"


