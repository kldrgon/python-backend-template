"""图像处理领域服务接口。"""
from abc import ABC, abstractmethod
from typing import BinaryIO, Tuple
from io import BytesIO


class ImageProcessor(ABC):
    """图像处理抽象接口。"""

    @abstractmethod
    async def compress_image(
        self,
        image_data: BinaryIO,
        max_bytes: int,
        mime_type: str | None = None,
    ) -> Tuple[BytesIO, str, int]:
        """压缩图像到指定大小。
        
        Args:
            image_data: 原始图像数据流
            max_bytes: 目标最大字节数
            mime_type: 图像MIME类型
            
        Returns:
            Tuple[BytesIO, str, int]: (压缩后的图像流, MIME类型, 实际大小)
            
        Raises:
            ValueError: 如果不是有效的图像格式
        """
        ...

