import asyncio
from io import BytesIO
import structlog
from typing import Optional, Tuple

from app.blob.domain.domain_service.thumbnail_cache import ThumbnailCache
from app.blob.domain.domain_service.storage_adapter import StorageAdapter, ObjectNotFoundError
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.mime_type import MimeType

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class BlobStorageThumbnailCacheAdapter(ThumbnailCache):
    """基于对象存储（S3/MinIO）的缩略图缓存适配器。
    
    将缩略图作为普通对象存储在同一 Provider/Bucket 下的 cache/thumbnails/ 目录中。
    """
    
    def __init__(
        self, 
        storage_adapter: StorageAdapter,
    ):
        self.storage_adapter = storage_adapter

    async def get(self, locator: StorageLocator) -> Optional[Tuple[int, str, BytesIO]]:
        try:
            # 1. 直接获取流，跳过显式的 exists 检查（get_object_stream 内部会做 head 操作）
            # 设置 skip_exists_check=True 以避免 get_object_stream 内部再次调用 object_exists
            meta, iterator = await self.storage_adapter.get_object_stream(
                locator, 
                chunk_size=1024 * 1024,
                skip_exists_check=True
            )
            
            # 2. 读取到内存（适配接口定义）
            cache_data = BytesIO()
            async for chunk in iterator:
                cache_data.write(chunk)
            cache_data.seek(0)
            
            mime_type = str(meta.mime_type) if meta.mime_type else "application/octet-stream"
            return meta.size_bytes, mime_type, cache_data
        
        except ObjectNotFoundError:
             # 缓存未命中
            return None
        except Exception as e:
            logger.warning("thumbnail_cache_read_error", error=str(e))
            return None

    async def put(self, locator: StorageLocator, data: BytesIO, mime_type: str) -> None:
        # 复制数据以防流被关闭或复用
        data_copy = BytesIO(data.getvalue())
        
        # 定义后台上传任务
        async def _upload():
            try:
                await self.storage_adapter.put_object(
                    locator,
                    data_copy,
                    mime_type=MimeType(value=mime_type)
                )
            except Exception as e:
                logger.error("thumbnail_cache_write_error", error=str(e))

        # 异步非阻塞执行
        asyncio.create_task(_upload())

