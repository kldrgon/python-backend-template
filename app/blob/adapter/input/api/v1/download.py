from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.blob.application.service.blob_external import BlobExternalCommandService
from app.blob.domain.domain_service.blob_public_service import BlobDownloadSignature
from app.blob.adapter.output.domain_service.blob_public_service import (
    InvalidBlobDownloadSignatureError,
    ExpiredBlobDownloadSignatureError,
)
from core.fastapi.dependencies.di.blob import get_blob_external_command_service
from core.response.rersponse_exception import ApiResponseException

router = APIRouter(
    tags=["blob"],
)


@router.get("/download", summary="通过签名下载文件（内部转发）")
async def download_by_signature(
    blob_id: Annotated[str, Query(..., description="文件ID")],
    exp: Annotated[int, Query(..., description="过期时间戳（秒）")],
    nonce: Annotated[str, Query(..., description="随机数")],
    sig: Annotated[str, Query(..., description="签名")],
    svc: Annotated[BlobExternalCommandService, Depends(get_blob_external_command_service)] = None,
):
    """
    通过签名下载文件，内部转发以避免直接访问CDN。
    签名参数通过query参数传递。
    """
    signature = BlobDownloadSignature(
        blob_id=blob_id,
        exp=exp,
        nonce=nonce,
        sig=sig,
    )

    try:
        blob_id = svc._public.verify_download_signature(signature=signature)
        blob_info, stream = await svc._public.open_stream(blob_id=blob_id)
    except InvalidBlobDownloadSignatureError as e:
        raise ApiResponseException(status_code=403, detail="无效的签名") from e
    except ExpiredBlobDownloadSignatureError as e:
        raise ApiResponseException(status_code=403, detail="签名已过期") from e
    except ValueError as e:
        raise ApiResponseException(status_code=404, detail=str(e)) from e

    headers = {}
    if blob_info.mime_type:
        headers["Content-Type"] = blob_info.mime_type
    if blob_info.display_name:
        headers["Content-Disposition"] = f'inline; filename="{blob_info.display_name}"'
    if blob_info.size_bytes:
        headers["Content-Length"] = str(blob_info.size_bytes)

    return StreamingResponse(
        stream,
        media_type=blob_info.mime_type or "application/octet-stream",
        headers=headers,
    )
