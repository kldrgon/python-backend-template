from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from app.blob.application.service.blob_external import BlobExternalCommandService
from app.blob.query.service import BlobQueryService
from app.blob.domain.domain_service.blob_file_domain_service import BlobFileDomainService
from app.blob.domain.domain_service.blob_attachment_service import BlobAttachmentDomainService
from app.blob.domain.domain_service.blob_public_service import BlobPublicDomainService
from .container import get_container

if TYPE_CHECKING:
    from app.container import Container


def get_blob_external_command_service(request: Request) -> BlobExternalCommandService:
    """获取Blob对外命令服务（外部系统：临时上传/验签下载）。"""
    container = get_container(request)
    return container.blob_container.blob_external_command_service()

def get_blob_file_domain_service(request: Request) -> BlobFileDomainService:
    """获取 Blob 文件领域服务（内部域使用：落库上传）。"""
    container = get_container(request)
    return container.blob_container.blob_file_domain_service()

def get_blob_public_domain_service(request: Request) -> BlobPublicDomainService:
    """获取 Blob 对外领域服务（内部域：签名下载/逻辑信息/打开流，不暴露存储细节）。"""
    container = get_container(request)
    return container.blob_container.blob_public_domain_service()


def get_blob_attachment_domain_service(request: Request) -> BlobAttachmentDomainService:
    """获取 Blob 附件领域服务（绑定引用）。"""
    container = get_container(request)
    return container.blob_container.blob_attachment_domain_service()


def get_blob_query_service(request: Request) -> BlobQueryService:
    """获取Blob读侧查询服务。"""
    container = get_container(request)
    return container.blob_container.blob_query_service()