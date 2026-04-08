from abc import ABC, abstractmethod
from typing import Optional, Tuple
from io import BytesIO
from app.blob.domain.entity.storage_locator import StorageLocator

class ThumbnailCache(ABC):
    """缩略图缓存服务接口（Port）。
    
    用于解耦具体的缓存实现（对象存储、Redis、CDN 等）。
    """

    @abstractmethod
    async def get(self, locator: StorageLocator) -> Optional[Tuple[int, str, BytesIO]]:
        """获取缓存的缩略图。
        
        Args:
            locator: 缩略图存储定位器（由聚合根生成）
            
        Returns:
            Optional[Tuple[int, str, BytesIO]]: (size_bytes, mime_type, data_stream)
            如果未命中缓存，返回 None。
        """
        ...

    @abstractmethod
    async def put(self, locator: StorageLocator, data: BytesIO, mime_type: str) -> None:
        """保存缩略图到缓存。
        
        Args:
            locator: 缩略图存储定位器（由聚合根生成）
            data: 图像数据流
            mime_type: 图像 MIME 类型
        """
        ...

