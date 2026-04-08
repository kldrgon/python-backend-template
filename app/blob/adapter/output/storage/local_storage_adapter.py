import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO, AsyncIterator, Tuple
from datetime import datetime
import shutil

from app.blob.domain.domain_service.storage_adapter import (
    StorageAdapter,
    ObjectMetadata,
    StorageError,
    ObjectNotFoundError,
)
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.etag import Etag
from app.blob.domain.vo.mime_type import MimeType


class LocalStorageAdapter(StorageAdapter):
    """本地文件系统存储适配器实现。"""
    
    def __init__(self, base_path: str = "./storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, locator: StorageLocator) -> Path:
        """根据存储定位器获取本地文件路径。"""
        return self.base_path / locator.bucket / locator.object_key
    
    def _calculate_etag(self, file_path: Path) -> str:
        """计算文件的ETag（使用MD5）。"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def put_object(
        self,
        locator: StorageLocator,
        body: BinaryIO,
        *,
        mime_type: Optional[MimeType] = None,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: Optional[str] = None
    ) -> ObjectMetadata:
        """将对象存储到本地文件系统。"""
        try:
            file_path = self._get_file_path(locator)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(file_path, "wb") as f:
                content = body.read()
                f.write(content)
            
            # 计算元数据
            size_bytes = len(content)
            etag = Etag(value=self._calculate_etag(file_path))
            last_modified = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            
            return ObjectMetadata(
                size_bytes=size_bytes,
                etag=etag,
                mime_type=mime_type,
                last_modified=last_modified,
                storage_class=storage_class or "STANDARD",
                custom_metadata=metadata
            )
            
        except Exception as e:
            raise StorageError(f"存储对象失败: {str(e)}", locator=locator, cause=e)
    
    async def head_object(self, locator: StorageLocator) -> Optional[ObjectMetadata]:
        """获取本地文件的元数据。"""
        try:
            file_path = self._get_file_path(locator)
            
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            etag = Etag(value=self._calculate_etag(file_path))
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            return ObjectMetadata(
                size_bytes=stat.st_size,
                etag=etag,
                last_modified=last_modified,
                storage_class="STANDARD"
            )
            
        except Exception as e:
            raise StorageError(f"获取对象元数据失败: {str(e)}", locator=locator, cause=e)
    
    async def delete_object(self, locator: StorageLocator) -> bool:
        """从本地文件系统删除对象。"""
        try:
            file_path = self._get_file_path(locator)
            
            if not file_path.exists():
                return False
            
            file_path.unlink()
            
            # 尝试删除空目录
            try:
                file_path.parent.rmdir()
            except OSError:
                pass  # 目录不为空，忽略
            
            return True
            
        except Exception as e:
            raise StorageError(f"删除对象失败: {str(e)}", locator=locator, cause=e)
    
    async def object_exists(self, locator: StorageLocator) -> bool:
        """检查本地文件是否存在。"""
        file_path = self._get_file_path(locator)
        return file_path.exists()
    
    async def get_object_url(
        self,
        locator: StorageLocator,
        *,
        expires_in_seconds: Optional[int] = None,
        skip_exists_check: bool = False,
    ) -> str:
        """生成本地文件的URL（file://协议）。
        
        Args:
            locator: 存储位置定位器
            expires_in_seconds: URL过期时间（秒），本地存储不使用此参数
            skip_exists_check: 是否跳过存在性检查以提升性能，默认 False
        """
        file_path = self._get_file_path(locator)
        
        # 仅在需要时检查文件存在性
        if not skip_exists_check and not file_path.exists():
            raise ObjectNotFoundError(f"对象不存在: {locator}", locator=locator)
        
        return f"file://{file_path.absolute()}"

    async def get_object_stream(
        self,
        locator: StorageLocator,
        *,
        chunk_size: int = 1024 * 1024,
        **kwargs
    ) -> Tuple[ObjectMetadata, AsyncIterator[bytes]]:
        """以流式方式读取本地文件内容。"""
        try:
            file_path = self._get_file_path(locator)
            skip_exists_check = kwargs.get("skip_exists_check", False)

            if not skip_exists_check and not file_path.exists():
                raise ObjectNotFoundError(f"对象不存在: {locator}", locator=locator)

            if not file_path.exists():
                raise ObjectNotFoundError(f"对象不存在: {locator}", locator=locator)

            stat = file_path.stat()
            mime_type_str, _ = mimetypes.guess_type(str(file_path))
            meta = ObjectMetadata(
                size_bytes=stat.st_size,
                etag=Etag(value=self._calculate_etag(file_path)),
                mime_type=MimeType(value=mime_type_str) if mime_type_str else None,
                last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                storage_class="STANDARD",
                custom_metadata={},
            )

            async def _iter() -> AsyncIterator[bytes]:
                try:
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                except Exception as e:
                    raise StorageError(f"下载流中断: {str(e)}", locator=locator, cause=e)

            return meta, _iter()
        except ObjectNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"下载对象失败: {str(e)}", locator=locator, cause=e)

    def supports_copy(self) -> bool:
        return True

    async def copy_object(
        self,
        *,
        source: StorageLocator,
        target: StorageLocator,
    ) -> ObjectMetadata:
        """本地文件系统拷贝对象。"""
        try:
            src_path = self._get_file_path(source)
            if not src_path.exists():
                raise ObjectNotFoundError(f"对象不存在: {source}", locator=source)

            dst_path = self._get_file_path(target)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)

            stat = dst_path.stat()
            etag = Etag(value=self._calculate_etag(dst_path))
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            return ObjectMetadata(
                size_bytes=stat.st_size,
                etag=etag,
                mime_type=None,
                last_modified=last_modified,
                storage_class="STANDARD",
                custom_metadata=None,
            )
        except ObjectNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"复制对象失败: {str(e)}", locator=target, cause=e)
