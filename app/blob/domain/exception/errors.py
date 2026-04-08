from __future__ import annotations

from app.blob.domain.vo.blob_status import BlobStatus


class InvalidBlobStatusError(Exception):
    """当 Blob 状态不满足某个领域操作的前置条件时抛出的异常。"""

    def __init__(self, *, blob_id: str, current_status: BlobStatus, expected_status: BlobStatus | None = None):
        self.blob_id = blob_id
        self.current_status = current_status
        self.expected_status = expected_status
        if expected_status is not None:
            msg = f"invalid blob status for operation: blob_id={blob_id}, status={current_status}, expected={expected_status}"
        else:
            msg = f"invalid blob status for operation: blob_id={blob_id}, status={current_status}"
        super().__init__(msg)



