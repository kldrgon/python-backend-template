from fastapi import APIRouter

from .upload import router as upload_router
from .download import router as download_router

router = APIRouter()
router.include_router(upload_router, prefix="/v1", tags=["blob"])
router.include_router(download_router, prefix="/v1", tags=["blob"])

__all__ = ["router"]
