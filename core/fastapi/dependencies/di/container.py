from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from app.container import Container


def get_container(request: Request) -> "Container":
    # Container instance attached in app/server.py
    return request.app.container  # type: ignore[attr-defined]