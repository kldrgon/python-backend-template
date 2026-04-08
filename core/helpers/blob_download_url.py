from __future__ import annotations

from urllib.parse import urlencode

from app.blob.domain.domain_service.blob_public_service import BlobDownloadSignature
from core.config import config


def build_internal_download_url(signature: BlobDownloadSignature) -> str:
    """
    构建内部下载URL（通过签名验证，避免直接访问CDN）。
    
    Args:
        signature: 下载签名信息
        
    Returns:
        完整的内部下载URL
    """
    base_url = config.blob_storage.internal_download_base_url.rstrip("/")
    params = {
        "blob_id": signature.blob_id,
        "exp": signature.exp,
        "nonce": signature.nonce,
        "sig": signature.sig,
    }
    query_string = urlencode(params)
    return f"{base_url}/v1/download?{query_string}"
