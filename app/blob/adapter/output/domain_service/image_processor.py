"""图像处理服务实现。"""
import io
from typing import BinaryIO, Tuple
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None

from app.blob.domain.domain_service.image_processor import ImageProcessor


class ImageProcessorImpl(ImageProcessor):
    """图像处理服务实现（基于 Pillow）。"""

    SUPPORTED_FORMATS = {
        'image/jpeg': 'JPEG',
        'image/jpg': 'JPEG',
        'image/png': 'PNG',
        'image/webp': 'WEBP',
        'image/bmp': 'BMP',
        'image/tiff': 'TIFF',
    }

    def _compress_sync(
        self,
        image_data: BinaryIO,
        max_bytes: int,
        mime_type: str | None = None,
    ) -> Tuple[BytesIO, str, int]:
        """同步压缩方法（运行在线程池中）"""
        if Image is None:
            raise ValueError("Pillow 未安装，无法处理图像")
        
        if hasattr(image_data, 'seek'):
            image_data.seek(0)
        
        try:
            img = Image.open(image_data)
            img.load()
        except Exception as e:
            raise ValueError(f"无法打开图像: {e}")
            
        format_str = None
        output_mime_type = mime_type
        
        if mime_type:
            format_str = self.SUPPORTED_FORMATS.get(mime_type.lower())
        
        if not format_str:
            if img.format:
                format_str = img.format.upper()
                if format_str == 'JPEG':
                    output_mime_type = 'image/jpeg'
                elif format_str == 'PNG':
                    output_mime_type = 'image/png'
                elif format_str == 'WEBP':
                    output_mime_type = 'image/webp'
                else:
                    format_str = 'JPEG'
                    output_mime_type = 'image/jpeg'
            else:
                format_str = 'JPEG'
                output_mime_type = 'image/jpeg'
        
        if format_str == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
            
        width, height = img.size
        current_pixels = width * height
        target_pixels = int(max_bytes / 0.2)
        
        scale = 1.0
        if current_pixels > target_pixels:
            scale = (target_pixels / current_pixels) ** 0.5
            
        if scale < 0.1: scale = 0.1
        
        if scale < 0.95:
            new_width = max(100, int(width * scale))
            new_height = max(100, int(height * scale))
            img = img.resize((new_width, new_height), Image.Resampling.BICUBIC)

        quality = 80
        
        final_buffer = BytesIO()
        save_kwargs = {'format': format_str, 'optimize': True}
        if format_str in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
            
        img.save(final_buffer, **save_kwargs)
        final_size = final_buffer.tell()
        
        if final_size > max_bytes:
            ratio = max_bytes / final_size
            rescale = (ratio ** 0.5) * 0.9
            if rescale < 0.1: rescale = 0.1
            
            width, height = img.size
            new_width = max(100, int(width * rescale))
            new_height = max(100, int(height * rescale))
            
            img = img.resize((new_width, new_height), Image.Resampling.BICUBIC)
            
            final_buffer = BytesIO()
            img.save(final_buffer, **save_kwargs)
            final_size = final_buffer.tell()

        final_buffer.seek(0)
        return final_buffer, output_mime_type, final_size

    async def compress_image(
        self,
        image_data: BinaryIO,
        max_bytes: int,
        mime_type: str | None = None,
    ) -> Tuple[BytesIO, str, int]:
        """压缩图像到指定大小（异步包装器）。"""
        from starlette.concurrency import run_in_threadpool
        
        return await run_in_threadpool(
            self._compress_sync,
            image_data,
            max_bytes,
            mime_type
        )
