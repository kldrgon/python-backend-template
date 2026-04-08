from fastapi import APIRouter

from app.user.adapter.input.api.v1 import router as user_v1_router

router = APIRouter()
router.include_router(user_v1_router, prefix="/user", tags=["user"])


__all__ = ["router"]
