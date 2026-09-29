from fastapi import APIRouter

from app.modules.activities import router as activities_router
from app.modules.auth import router as auth_router
from app.modules.participants import admin_router as participants_admin_router, router as participants_router
from app.modules.chat import admin_router as chat_admin_router, router as chat_router
from app.modules.danmaku import admin_router as danmaku_admin_router
from app.modules.danmaku import router as danmaku_router
from app.modules.lottery import router as lottery_router
from app.modules.sms import router as sms_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(activities_router)
api_router.include_router(participants_router)
api_router.include_router(participants_admin_router)
api_router.include_router(chat_router)
api_router.include_router(chat_admin_router)
api_router.include_router(danmaku_admin_router)
api_router.include_router(danmaku_router)
api_router.include_router(lottery_router.admin_router)
api_router.include_router(lottery_router.router)
api_router.include_router(sms_router)


@api_router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
