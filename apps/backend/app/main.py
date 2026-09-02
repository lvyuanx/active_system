from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.modules.auth import ensure_superuser
from app.modules.danmaku.testing import danmaku_test_manager
from app.modules.chat.stickers import scan_chat_sticker_media
from app.modules.lottery.media_service import scan_lottery_media

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_superuser(settings)
    scan_lottery_media(settings)
    scan_chat_sticker_media(settings)
    try:
        yield
    finally:
        await danmaku_test_manager.stop_all()


app = FastAPI(
    title="活动系统 API",
    version="0.1.0",
    description="活动管理、用户参与和实时大屏服务。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex="null",
)
app.include_router(api_router)
