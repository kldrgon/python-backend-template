from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.blob.application.exception import BlobStorageNotConfiguredException
from app.blob.application.service.blob_external import BlobExternalCommandService
from core.fastapi.dependencies.di.blob import (
    get_blob_external_command_service,
)
from core.fastapi.dependencies.permission import IsAuthenticated, PermissionDependency
from core.helpers.blob_download_url import build_internal_download_url
from core.response import ApiResponse
from core.response.rersponse_exception import ApiResponseException

router = APIRouter(
    tags=["blob"],
    dependencies=[Depends(PermissionDependency([IsAuthenticated]))],
)


@router.post("/upload", summary="上传文件（临时）", status_code=201)
async def upload_temp_file(
    file: Annotated[UploadFile, File(..., description="文件")],
    svc: Annotated[BlobExternalCommandService, Depends(get_blob_external_command_service)] = None,
    owner_type: Optional[str] = Query(None, description="引用方类型，如 'user'、'post'"),
    owner_id: Optional[str] = Query(None, description="引用方 ID"),
    edge_key: Optional[str] = Query(None, description="语义键，如 'avatar'、'cover'"),
):
    """
    供前端/外部系统使用：
    - 返回 blob_id
    - 若提供 owner_type / owner_id / edge_key，则同时建立引用关系
    - 尝试返回可直接访问的 download_url（若存储未配置或生成失败则为 null）
    """
    try:
        blob_id = await svc.upload_temp(
            fileobj=file.file,
            content_type=file.content_type,
            display_name=file.filename,
            owner_type=owner_type,
            owner_id=owner_id,
            edge_key=edge_key,
        )
    except BlobStorageNotConfiguredException as e:
        raise ApiResponseException(status_code=500, detail=str(e)) from e

    download_url = None
    try:
        signature = await svc.get_download_signature(blob_id=blob_id)
        download_url = build_internal_download_url(signature)
    except Exception:
        download_url = None

    return ApiResponse.created(data={"blob_id": blob_id, "download_url": download_url})
