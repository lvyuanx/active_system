import asyncio
from json import JSONDecodeError
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import Settings, get_settings
from app.modules.chat.manager import chat_manager
from app.modules.chat.service import ChatMessagePage, ChatReadOnlyError, create_message, list_messages
from app.modules.participants.router import ActivityPrincipal, bearer, get_activity_principal


router = APIRouter(prefix="/activities", tags=["chat"])


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
            body = message.get("body")
            if not isinstance(body, str):
                await _send_error(websocket, "invalid_body", "消息正文必须是文本")
                continue
            try:
                created = await asyncio.to_thread(create_message, activity_id, principal, body, settings)
            except ChatReadOnlyError:
                await _send_error(websocket, "read_only", "当前活动暂不可发言")
                continue
            except ValueError as error:
                await _send_error(websocket, "invalid_body", str(error))
                continue
            payload = {"type": "message.created", "message": created.model_dump(mode="json")}
            await chat_manager.broadcast(activity_id, payload)
    finally:
        if principal is not None:
            await chat_manager.disconnect(activity_id, websocket)
