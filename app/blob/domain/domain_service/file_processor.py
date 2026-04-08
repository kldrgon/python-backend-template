from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class FileProcessorService(ABC):
    """文件处理领域服务接口。
    
    负责文件的哈希计算等技术细节，从聚合根中分离基础设施关注点。
    """
    
    @abstractmethod
    async def compute_hash_and_size(self, fileobj: BinaryIO) -> tuple[str, int]:
        """计算文件的 SHA256 哈希和大小。
        
        Args:
            fileobj: 二进制文件对象
            
        Returns:
            元组 (sha256_hex, size_bytes)
        """
        ...

