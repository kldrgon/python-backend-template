from fastapi import APIRouter

from app.blob.adapter.input.api.v1 import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/blob", tags=["blob"])

__all__ = ["router"]
