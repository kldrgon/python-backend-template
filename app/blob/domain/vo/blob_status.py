from enum import Enum


class BlobStatus(str, Enum):
    """Blob 处理状态枚举。"""
    PENDING = "pending"  # 待处理：已创建记录，等待 hash256 计算和存储上传
    PROCESSING = "processing"  # 处理中：正在计算 hash256 和上传存储
    READY = "ready"  # 就绪：hash256 和存储位置已就绪，可以使用
    FAILED = "failed"  # 失败：处理失败

