from fastapi import Request

from app.blob.domain.domain_service.blob_public_service import BlobPublicDomainService
from app.user.application.port.avatar_url_port import AvatarUrlPort
from core.fastapi.dependencies.di import get_blob_public_domain_service


class AvatarUrlAdapter(AvatarUrlPort):
    def __init__(self, svc: BlobPublicDomainService):
        self._svc = svc

    async def get_avatar_url(self, *, blob_id: str) -> str | None:
        try:
            return await self._svc.create_download_url(blob_id=blob_id)
        except Exception:
            return None


def get_avatar_url_adapter(request: Request) -> AvatarUrlPort:
    return AvatarUrlAdapter(get_blob_public_domain_service(request))
