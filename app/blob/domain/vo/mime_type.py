import re
import mimetypes
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class MimeType(BaseModel):
    """MIME 类型值对象。"""
    
    value: str = Field(..., description="MIME 类型值")
    
    @field_validator("value")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        if not v:
            raise ValueError("MIME 类型不能为空")
            
        # 基础格式校验：type/subtype
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_.]*$", v):
            raise ValueError(f"非法的 MIME 类型格式: {v}")
            
        return v.lower()
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other) -> bool:
        if isinstance(other, MimeType):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other.lower()
        return False
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    @property
    def main_type(self) -> str:
        """获取主类型（斜杠前）。"""
        return self.value.split("/")[0]
    
    @property
    def sub_type(self) -> str:
        """获取子类型（斜杠后）。"""
        return self.value.split("/")[1]
    
    def is_text(self) -> bool:
        """是否为文本类型。"""
        return self.main_type == "text"
    
    def is_image(self) -> bool:
        """是否为图片类型。"""
        return self.main_type == "image"
    
    def is_video(self) -> bool:
        """是否为视频类型。"""
        return self.main_type == "video"
    
    def is_audio(self) -> bool:
        """是否为音频类型。"""
        return self.main_type == "audio"
    
    def is_application(self) -> bool:
        """是否为 application 类型。"""
        return self.main_type == "application"

    @classmethod
    def from_extension(cls, extension: str, strict: bool = False) -> "MimeType":
        """基于文件扩展名创建 `MimeType`（使用标准库 mimetypes）。

        Args:
            extension: 文件扩展名，如 ".png" 或 "png"。
            strict: 若为 True，未知扩展名将抛出异常；否则回退为 octet-stream。
        """
        if not extension:
            if strict:
                raise ValueError("文件扩展名不能为空")
            return APPLICATION_OCTET_STREAM

        ext = extension if extension.startswith(".") else f".{extension}"
        # 初始化 mimetypes（幂等）以确保类型映射完整
        mimetypes.init()
        mime = mimetypes.types_map.get(ext)
        if mime is None:
            # 同时尝试 common_types
            mime = mimetypes.common_types.get(ext)
        if mime is None:
            if strict:
                raise ValueError(f"未知的文件扩展名: {extension}")
            return APPLICATION_OCTET_STREAM
        return cls(value=mime)

    @classmethod
    def from_filename(cls, filename: str, strict: bool = False) -> "MimeType":
        """基于文件名使用 mimetypes.guess_type 推断 `MimeType`。

        未知时返回 application/octet-stream（除非 strict=True）。
        """
        if not filename:
            if strict:
                raise ValueError("文件名不能为空")
            return APPLICATION_OCTET_STREAM
        mimetypes.init()
        guessed, _ = mimetypes.guess_type(filename)
        if guessed is None:
            if strict:
                raise ValueError(f"无法根据文件名推断 MIME 类型: {filename}")
            return APPLICATION_OCTET_STREAM
        return cls(value=guessed)

    @classmethod
    def from_bytes(cls, data: bytes, strict: bool = False) -> "MimeType":
        """基于字节内容识别 `MimeType`（在可用时使用 `python-magic`）。

        该功能依赖可选库 `python-magic`。若不可用或识别失败，返回 application/octet-stream（除非 strict=True）。
        """
        if data is None:
            if strict:
                raise ValueError("数据字节不能为空")
            return APPLICATION_OCTET_STREAM
        try:
            import magic  # type: ignore
            detected: Optional[str] = magic.from_buffer(data, mime=True)  # type: ignore
            if not detected:
                if strict:
                    raise ValueError("无法根据字节内容识别 MIME 类型")
                return APPLICATION_OCTET_STREAM
            return cls(value=str(detected))
        except Exception:
            if strict:
                raise
            return APPLICATION_OCTET_STREAM


# 常用 MIME 类型常量
TEXT_PLAIN = MimeType(value="text/plain")
TEXT_HTML = MimeType(value="text/html")
TEXT_MARKDOWN = MimeType(value="text/markdown")
APPLICATION_JSON = MimeType(value="application/json")
APPLICATION_PDF = MimeType(value="application/pdf")
APPLICATION_OCTET_STREAM = MimeType(value="application/octet-stream")
