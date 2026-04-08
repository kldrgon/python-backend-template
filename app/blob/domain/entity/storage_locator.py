from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional

from app.blob.domain.vo.hash import SHA256Hash


class StorageLocator(BaseModel):
    """存储位置实体。
    
    通过 storage_locator_id 唯一标识。
    sha256 用于快速查询与排查，从关联的 Blob 同步。
    unique_key (storage_provider:bucket:object_key) 保留用于显示，但不再作为唯一性约束。
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    
    storage_locator_id: Optional[str] = Field(None, description="业务标识符（UUID hex）")
    storage_provider: str = Field(..., description="存储提供方名称（如 's3'、'gcs'、'azure'）")
    bucket: str = Field(..., description="存储桶或容器名称")
    object_key: str = Field(..., description="桶内对象键或路径")
    region: Optional[str] = Field(None, description="存储区域")
    sha256: Optional[SHA256Hash] = Field(None, description="SHA256 哈希值（从 Blob 同步）")
    
    @field_validator("storage_provider")
    @classmethod
    def validate_storage_provider(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("存储提供方不能为空")
        return v.strip().lower()
    
    @field_validator("bucket")
    @classmethod
    def validate_bucket(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("桶名不能为空")
        # 桶名基础校验（可依据提供方扩展）
        if len(v) < 3 or len(v) > 63:
            raise ValueError("桶名长度必须在 3 到 63 之间")
        return v.strip().lower()
    
    @field_validator("object_key")
    @classmethod
    def validate_object_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("对象键不能为空")
        # 去除首尾空白但保留内部结构
        return v.strip()
    
    @field_validator("sha256", mode="before")
    @classmethod
    def validate_sha256_hash(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return SHA256Hash(value=v)
        return v
    
    def __str__(self) -> str:
        region_part = f"@{self.region}" if self.region else ""
        return f"{self.storage_provider}://{self.bucket}/{self.object_key}{region_part}"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, StorageLocator):
            return False
        # 通过 unique_key 比较
        return (
            self.storage_provider == other.storage_provider
            and self.bucket == other.bucket
            and self.object_key == other.object_key
            and self.region == other.region
        )
    
    def __hash__(self) -> int:
        # 基于 unique_key 计算哈希
        return hash((self.storage_provider, self.bucket, self.object_key, self.region))
    
    @property
    def unique_key(self) -> str:
        """获取用于存储位置约束的唯一键。"""
        return f"{self.storage_provider}:{self.bucket}:{self.object_key}"
    
    
    def is_s3_compatible(self) -> bool:
        """是否为 S3 兼容的存储提供方。"""
        return self.storage_provider in ["s3", "minio", "digitalocean", "wasabi"]
    
    def is_google_cloud(self) -> bool:
        """是否为 Google Cloud 存储。"""
        return self.storage_provider == "gcs"
    
    def is_azure(self) -> bool:
        """是否为 Azure Blob 存储。"""
        return self.storage_provider in ["azure", "azureblob"]

