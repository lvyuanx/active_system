from fastapi import APIRouter

from app.modules.activities import router as activities_router
from app.modules.auth import router as auth_router
from app.modules.participants import router as participants_router
from app.modules.chat import router as chat_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(activities_router)
api_router.include_router(participants_router)
api_router.include_router(chat_router)


@api_router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
