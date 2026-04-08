from fastapi import APIRouter

from app.auth.adapter.input.api.v1 import router as auth_v1_router

router = APIRouter()
router.include_router(auth_v1_router, prefix="/auth", tags=["auth"])

__all__ = ["router"]
