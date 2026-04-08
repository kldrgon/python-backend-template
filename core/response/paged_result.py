from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PagedResult(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list, description="分页数据项")
    total: int = Field(default=0, description="总数量（不受 limit/offset 影响）")
    limit: int = Field(default=10, description="本次分页大小")
    offset: int = Field(default=0, description="偏移量")


try:
    PagedResult.model_rebuild()
except Exception:
    pass

