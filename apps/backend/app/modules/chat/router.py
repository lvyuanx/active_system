import asyncio
from json import JSONDecodeError
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket
from fastapi import WebSocketDisconnect, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.modules.chat.manager import chat_manager
from app.modules.chat.service import (
    ChatMessagePage,
    ChatInvalidStickerError,
    ChatMutedError,
    ChatParticipantInactiveError,
    ChatReadOnlyError,
    create_message,
    list_messages,
)
from app.modules.chat.stickers import (
    ChatSticker,
    ChatStickerAdminResponse,
    ChatStickerError,
    create_sticker,
    get_sticker_image_file,
    list_stickers,
    set_sticker_enabled,
)
from app.modules.files.service import MediaError
from app.modules.danmaku.manager import danmaku_manager
from app.modules.auth import require_superuser
from app.modules.participants.router import ActivityPrincipal, bearer, get_activity_principal


router = APIRouter(prefix="/activities", tags=["chat"])
admin_router = APIRouter(prefix="/admin/activities", tags=["chat-admin"])


def _sticker_http_error(error: ChatStickerError) -> HTTPException:
    if error.code in {"sticker_not_found", "image_not_found"}:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.detail)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.detail)


def _media_http_error(error: MediaError) -> HTTPException:
    if error.code == "image_too_large":
        return HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=error.detail)
    if error.code == "storage_error":
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error.detail)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.detail)


@admin_router.get("/{activity_id}/chat/stickers", response_model=list[ChatStickerAdminResponse])
def get_admin_stickers(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> list[ChatStickerAdminResponse]:
    try:
        return list_stickers(activity_id, settings, enabled_only=False)  # type: ignore[return-value]
    except ChatStickerError as error:
        raise _sticker_http_error(error) from error


@admin_router.post(
    "/{activity_id}/chat/stickers",
    response_model=ChatStickerAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_admin_sticker(
    activity_id: str,
    file: UploadFile = File(...),
    name: str | None = Form(None),
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ChatStickerAdminResponse:
    try:
        return await create_sticker(activity_id, file, settings, name)
    except ChatStickerError as error:
        raise _sticker_http_error(error) from error
    except MediaError as error:
        raise _media_http_error(error) from error


@admin_router.delete(
    "/{activity_id}/chat/stickers/{sticker_id}",
    response_model=ChatStickerAdminResponse,
)
def disable_admin_sticker(
    activity_id: str,
    sticker_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ChatStickerAdminResponse:
    try:
        return set_sticker_enabled(activity_id, sticker_id, settings, enabled=False)
    except ChatStickerError as error:
        raise _sticker_http_error(error) from error


@admin_router.post(
    "/{activity_id}/chat/stickers/{sticker_id}/restore",
    response_model=ChatStickerAdminResponse,
)
def restore_admin_sticker(
    activity_id: str,
    sticker_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ChatStickerAdminResponse:
    try:
        return set_sticker_enabled(activity_id, sticker_id, settings, enabled=True)
    except ChatStickerError as error:
        raise _sticker_http_error(error) from error


@router.get("/{activity_id}/chat/stickers", response_model=list[ChatSticker])
def get_activity_stickers(
    activity_id: str,
    _: ActivityPrincipal = Depends(get_activity_principal),
    settings: Settings = Depends(get_settings),
) -> list[ChatSticker]:
    try:
        return list_stickers(activity_id, settings, enabled_only=True)  # type: ignore[return-value]
    except ChatStickerError as error:
        raise _sticker_http_error(error) from error


@router.get("/{activity_id}/chat/stickers/{sticker_id}/image")
def get_public_sticker_image(
    activity_id: str,
    sticker_id: int,
    version: Annotated[str, Query(alias="v", min_length=1, max_length=100)],
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        image = get_sticker_image_file(activity_id, sticker_id, version, settings)
    except ChatStickerError as error:
        raise _sticker_http_error(error) from error
    return FileResponse(
        image.path,
        media_type=image.mime,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{activity_id}/chat/messages", response_model=ChatMessagePage)
def get_messages(
    activity_id: str,
    principal: ActivityPrincipal = Depends(get_activity_principal),
    settings: Settings = Depends(get_settings),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before_id: Annotated[int | None, Query(ge=1)] = None,
    after_id: Annotated[int | None, Query(ge=1)] = None,
) -> ChatMessagePage:
    return list_messages(
        activity_id,
        principal,
        settings,
        limit=limit,
        before_id=before_id,
        after_id=after_id,
    )


def _authenticate_websocket(activity_id: str, token: str, settings: Settings) -> ActivityPrincipal:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return get_activity_principal(activity_id, credentials, settings)


async def _send_error(websocket: WebSocket, code: str, detail: str) -> None:
    await websocket.send_json({"type": "chat.error", "code": code, "detail": detail})


@router.websocket("/{activity_id}/chat/ws")
async def chat_websocket(activity_id: str, websocket: WebSocket, settings: Settings = Depends(get_settings)) -> None:
    await websocket.accept()
    principal: ActivityPrincipal | None = None
    try:
        try:
            auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        except (asyncio.TimeoutError, WebSocketDisconnect):
            await websocket.close(code=1008)
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
            await _send_error(websocket, "unauthorized", "活动登录已失效")
            await websocket.close(code=1008)
            return
        try:
            principal = await asyncio.to_thread(_authenticate_websocket, activity_id, token, settings)
        except HTTPException as error:
            await _send_error(websocket, "unauthorized", str(error.detail))
            await websocket.close(code=1008)
            return
        except jwt.InvalidTokenError:
            await _send_error(websocket, "unauthorized", "活动登录已失效")
            await websocket.close(code=1008)
            return
        await chat_manager.connect(activity_id, websocket)
        await websocket.send_json(
            {
                "type": "chat.ready",
                "activity_id": activity_id,
                "activity_user_id": principal.activity_user_id,
            }
        )
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except (JSONDecodeError, ValueError, TypeError):
                await _send_error(websocket, "protocol_error", "消息必须是合法 JSON")
                continue
            if not isinstance(message, dict) or message.get("type") != "message.send":
                await _send_error(websocket, "protocol_error", "不支持的消息类型")
                continue
            sticker_id = message.get("sticker_id")
            if sticker_id is not None:
                if "body" in message or isinstance(sticker_id, bool) or not isinstance(sticker_id, int):
                    await _send_error(websocket, "invalid_sticker", "表情消息不能同时发送文字")
                    continue
                body = None
            else:
                body = message.get("body")
                if not isinstance(body, str):
                    await _send_error(websocket, "invalid_body", "消息正文必须是文本")
                    continue
            try:
                created = await asyncio.to_thread(
                    create_message,
                    activity_id,
                    principal,
                    body,
                    settings,
                    sticker_id=sticker_id,
                )
            except ChatReadOnlyError:
                await _send_error(websocket, "read_only", "当前活动暂不可发言")
                continue
            except ChatMutedError:
                await _send_error(websocket, "muted", "你已被禁言")
                continue
            except ChatParticipantInactiveError:
                await _send_error(websocket, "unauthorized", "活动登录已失效")
                await websocket.close(code=1008)
                return
            except ChatInvalidStickerError:
                await _send_error(websocket, "invalid_sticker", "表情不存在、已下架或不属于当前活动")
                continue
            except ValueError as error:
                await _send_error(websocket, "invalid_body", str(error))
                continue
            payload = {"type": "message.created", "message": created.model_dump(mode="json")}
            await chat_manager.broadcast(activity_id, payload)
            await danmaku_manager.broadcast_message(activity_id, created.model_dump(mode="json"))
    finally:
        if principal is not None:
            await chat_manager.disconnect(activity_id, websocket)
