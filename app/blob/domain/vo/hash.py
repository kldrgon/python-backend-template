import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, ValidationInfo


class Hash(BaseModel):
    """用于完整性校验的内容哈希值对象（当前仅支持 sha256）。"""

    # 继承体系保留：Hash -> SHA256Hash
    algorithm: Literal["sha256"] = Field(default="sha256", description="哈希算法")
    value: str = Field(..., description="哈希值")

    @field_validator("value")
    @classmethod
    def validate_hash_format(cls, v: str, info: ValidationInfo) -> str:
        algorithm = info.data.get("algorithm", "sha256")
        if algorithm != "sha256":
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        if not re.match(r"^[a-fA-F0-9]{64}$", v):
            raise ValueError("SHA256 哈希必须为 64 位十六进制字符")
        return v.lower()

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, Hash):
            return self.value == other.value and self.algorithm == other.algorithm
        if isinstance(other, str):
            return self.value == other.lower()
        return False

    def __hash__(self) -> int:
        return hash((self.value, self.algorithm))


class SHA256Hash(Hash):
    """SHA256 哈希值对象。"""

    def __init__(self, value: str, **kwargs):
        super().__init__(value=value, algorithm="sha256")
