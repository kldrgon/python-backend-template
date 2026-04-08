from typing import Literal

from pydantic import BaseModel


class MediaStateDTO(BaseModel):
    blob_id: str
    status: Literal["available", "unavailable", "unknown"]
