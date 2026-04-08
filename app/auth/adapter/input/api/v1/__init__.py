from fastapi import APIRouter

from .auth import auth_router
from .miniapp import router as miniapp_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router)
router.include_router(miniapp_router)