from __future__ import annotations

import hashlib
from typing import BinaryIO

from app.blob.domain.domain_service.file_processor import FileProcessorService


class SqlAlchemyFileProcessorService(FileProcessorService):
    """文件处理服务的实现。"""
    
    async def compute_hash_and_size(self, fileobj: BinaryIO) -> tuple[str, int]:
        """计算文件的 SHA256 哈希和大小。"""
        sha256 = hashlib.sha256()
        total_size = 0
        
        try:
            fileobj.seek(0)
        except Exception:
            pass
        
        chunk_size = 1024 * 1024
        while True:
            chunk = fileobj.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            sha256.update(chunk)
        
        try:
            fileobj.seek(0)
        except Exception:
            pass
        
        return sha256.hexdigest(), total_size
