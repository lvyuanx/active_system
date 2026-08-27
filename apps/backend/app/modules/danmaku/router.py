import asyncio
from json import JSONDecodeError
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.modules.auth import require_superuser
from app.modules.danmaku.manager import danmaku_manager
from app.modules.danmaku.service import (
    DanmakuAdminResponse,
    DanmakuMessagePage,
    DanmakuPrincipal,
    DanmakuSessionResponse,
    DanmakuSettingsUpdate,
    authenticate_danmaku_token,
    get_danmaku_record,
    get_danmaku_session,
    list_danmaku_messages,
    make_admin_response,
    regenerate_danmaku_token,
    update_danmaku_settings,
)


admin_router = APIRouter(prefix="/admin/activities", tags=["danmaku-admin"])
router = APIRouter(prefix="/danmaku", tags=["danmaku"])
danmaku_bearer = HTTPBearer(auto_error=False)


def get_danmaku_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(danmaku_bearer),
    settings: Settings = Depends(get_settings),
) -> DanmakuPrincipal:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请提供弹幕 token")
    return authenticate_danmaku_token(credentials.credentials, settings)


@admin_router.get("/{activity_id}/danmaku", response_model=DanmakuAdminResponse)
def get_admin_danmaku(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> DanmakuAdminResponse:
    return make_admin_response(get_danmaku_record(activity_id, settings), settings)


@admin_router.put("/{activity_id}/danmaku", response_model=DanmakuAdminResponse)
async def save_admin_danmaku(
    activity_id: str,
    payload: DanmakuSettingsUpdate,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> DanmakuAdminResponse:
    record = await asyncio.to_thread(update_danmaku_settings, activity_id, payload, settings)
    response = make_admin_response(record, settings)
    await danmaku_manager.broadcast(
        activity_id,
        {"type": "danmaku.settings.updated", "settings": response.settings.model_dump(mode="json")},
    )
    return response


@admin_router.post("/{activity_id}/danmaku/token", response_model=DanmakuAdminResponse)
async def rotate_admin_danmaku_token(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> DanmakuAdminResponse:
    record = await asyncio.to_thread(regenerate_danmaku_token, activity_id, settings)
    await danmaku_manager.invalidate_activity(activity_id, record.token_version)
    return make_admin_response(record, settings)


@router.get("/session", response_model=DanmakuSessionResponse)
def get_session(
    principal: DanmakuPrincipal = Depends(get_danmaku_principal),
    settings: Settings = Depends(get_settings),
) -> DanmakuSessionResponse:
    return get_danmaku_session(principal, settings)


@router.get("/messages", response_model=DanmakuMessagePage)
def get_messages(
    principal: DanmakuPrincipal = Depends(get_danmaku_principal),
    settings: Settings = Depends(get_settings),
    after_id: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> DanmakuMessagePage:
    return list_danmaku_messages(principal, settings, after_id=after_id, limit=limit)


async def _send_error(websocket: WebSocket, code: str, detail: str) -> None:
    await websocket.send_json({"type": "danmaku.error", "code": code, "detail": detail})


def _authenticate_websocket(token: str, settings: Settings) -> DanmakuPrincipal:
    return authenticate_danmaku_token(token, settings)


@router.websocket("/ws")
async def danmaku_websocket(websocket: WebSocket, settings: Settings = Depends(get_settings)) -> None:
    await websocket.accept()
    principal: DanmakuPrincipal | None = None
    try:
        try:
            auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        except asyncio.TimeoutError:
            await websocket.close(code=1008)
            return
        except WebSocketDisconnect:
            return
        except (JSONDecodeError, ValueError, TypeError):
            await _send_error(websocket, "protocol_error", "消息必须是合法 JSON")
            await websocket.close(code=1008)
            return
        if not isinstance(auth_message, dict) or auth_message.get("type") != "auth":
            await _send_error(websocket, "protocol_error", "首条消息必须是 auth")
            await websocket.close(code=1008)
            return
        token = auth_message.get("token")
        if not isinstance(token, str) or not token:
            await _send_error(websocket, "unauthorized", "弹幕 token 无效或已失效")
            await websocket.close(code=1008)
            return
        try:
            principal = await asyncio.to_thread(_authenticate_websocket, token, settings)
        except HTTPException as error:
            await _send_error(websocket, "unauthorized", str(error.detail))
            await websocket.close(code=1008)
            return
        connected = await danmaku_manager.connect(
            principal.activity_id,
            websocket,
            principal.token_version,
        )
        if not connected:
            await _send_error(websocket, "unauthorized", "弹幕 token 无效或已失效")
            await websocket.close(code=1008)
            return
        session = await asyncio.to_thread(get_danmaku_session, principal, settings)
        await websocket.send_json({"type": "danmaku.ready", "session": session.model_dump(mode="json")})
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except (JSONDecodeError, ValueError, TypeError):
                await _send_error(websocket, "protocol_error", "消息必须是合法 JSON")
                continue
            if not isinstance(message, dict) or message.get("type") != "ping":
                await _send_error(websocket, "protocol_error", "不支持的消息类型")
                continue
            await websocket.send_json({"type": "danmaku.pong"})
    finally:
        if principal is not None:
            await danmaku_manager.disconnect(principal.activity_id, websocket)
