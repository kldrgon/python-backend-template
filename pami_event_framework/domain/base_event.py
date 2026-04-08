"""事件基类"""

from abc import ABC
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional, Union
import uuid

from pydantic import BaseModel


class BaseEvent(ABC):
    """
    事件基类。

    提供通用事件元数据：event_id、event_type、occurred_at、version、payload。
    具体语义由子类区分，例如领域事件或应用事件。
    """

    event_type: ClassVar[str] = ""

    def __init__(self, payload: Optional[Union[BaseModel, Dict[str, Any]]] = None, **kwargs):
        self.event_id = str(uuid.uuid4())
        self.event_type = self.event_type or self.__class__.__name__
        self.occurred_at = datetime.now(timezone.utc)
        self.version = 1

        if payload is None:
            payload_data = dict(kwargs)
        elif isinstance(payload, BaseModel):
            payload_data = payload.model_dump()
            payload_data.update(kwargs)
        elif isinstance(payload, dict):
            payload_data = dict(payload)
            payload_data.update(kwargs)
        else:
            raise TypeError("payload必须是BaseModel或dict")

        self.payload = payload_data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "payload": self.payload,
        }

    def get_payload(self) -> Dict[str, Any]:
        return self.payload

    def set_payload(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEvent":
        event = cls(**data.get("payload", {}))
        event.event_id = data.get("event_id", event.event_id)
        event.version = data.get("version", 1)

        if "occurred_at" in data:
            if isinstance(data["occurred_at"], str):
                event.occurred_at = datetime.fromisoformat(
                    data["occurred_at"].replace("Z", "+00:00")
                )
            else:
                event.occurred_at = data["occurred_at"]
        return event

    def __repr__(self) -> str:
        return f"[{self.event_type}](event_id={self.event_id}, occurred_at={self.occurred_at})"
