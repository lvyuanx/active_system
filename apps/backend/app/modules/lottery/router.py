import asyncio
from json import JSONDecodeError, loads
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token_payload
from app.modules.auth import require_superuser
from app.modules.lottery.manager import lottery_manager
from app.modules.lottery.models import (
    LotteryEntryPage,
    LotteryEntryStatus,
    LotteryEntryUpdate,
    LotteryEntryUpdateResponse,
    LotteryPrizeImageResponse,
    LotterySecurityCodeRequest,
    LotterySecurityCodeResponse,
)
from app.modules.files.service import MediaError
from app.modules.lottery.media_service import (
    get_prize_image_file,
    remove_prize_image,
    replace_prize_image,
)
from app.modules.lottery.service import (
    LotteryConfigError,
    LotteryConfigResponse,
    LotteryConfigUpdate,
    LotteryHistoryPage,
    get_lottery_entries,
    get_lottery_config,
    get_lottery_snapshot,
    list_lottery_history,
    public_config,
    verify_lottery_security_code,
    update_lottery_entry,
    update_lottery_config,
)
from .protocol import handle_admin_lottery_message, send_lottery_error
from .round_state import lottery_round_store, lottery_selection_store
from .state import lottery_operation_lock


admin_router = APIRouter(prefix="/admin/activities", tags=["lottery-admin"])
router = APIRouter(prefix="/activities", tags=["lottery"])


def _config_http_error(error: LotteryConfigError) -> HTTPException:
    if error.code in {
        "activity_not_found",
        "entry_not_found",
        "invalid_prize",
        "image_not_found",
    }:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.detail)
    if error.code in {"config_conflict", "prize_has_draws", "quantity_below_draws", "draw_in_progress"}:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail)
    if error.code == "security_code_invalid":
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.detail)
    if error.code == "security_code_not_configured":
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.detail)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.detail)


def _image_http_error(error: MediaError) -> HTTPException:
    if error.code == "image_too_large":
        return HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=error.detail)
    if error.code == "storage_error":
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error.detail)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.detail)


@admin_router.post(
    "/{activity_id}/lottery/prizes/{prize_id}/image",
    response_model=LotteryPrizeImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_admin_prize_image(
    activity_id: str,
    prize_id: int,
    file: UploadFile = File(...),
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> LotteryPrizeImageResponse:
    async with lottery_operation_lock:
        if lottery_round_store.get(activity_id):
            raise _config_http_error(LotteryConfigError("draw_in_progress", "抽奖进行中，暂不能修改抽奖配置"))
        try:
            response = await replace_prize_image(activity_id, prize_id, file, settings)
            config = await asyncio.to_thread(get_lottery_config, activity_id, settings)
        except LotteryConfigError as error:
            raise _config_http_error(error) from error
        except MediaError as error:
            raise _image_http_error(error) from error
        await lottery_manager.broadcast(
            activity_id,
            {"type": "lottery.config.updated", "config": public_config(config)},
        )
        return response


@admin_router.delete(
    "/{activity_id}/lottery/prizes/{prize_id}/image",
    response_model=LotteryPrizeImageResponse,
)
async def delete_admin_prize_image(
    activity_id: str,
    prize_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> LotteryPrizeImageResponse:
    async with lottery_operation_lock:
        if lottery_round_store.get(activity_id):
            raise _config_http_error(LotteryConfigError("draw_in_progress", "抽奖进行中，暂不能修改抽奖配置"))
        try:
            response = await asyncio.to_thread(remove_prize_image, activity_id, prize_id, settings)
            config = await asyncio.to_thread(get_lottery_config, activity_id, settings)
        except LotteryConfigError as error:
            raise _config_http_error(error) from error
        await lottery_manager.broadcast(
            activity_id,
            {"type": "lottery.config.updated", "config": public_config(config)},
        )
        return response


@admin_router.get("/{activity_id}/lottery/prizes/{prize_id}/image")
def get_admin_prize_image(
    activity_id: str,
    prize_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
    version: Annotated[str | None, Query(alias="v", max_length=100)] = None,
) -> FileResponse:
    try:
        image = get_prize_image_file(activity_id, prize_id, version, settings)
    except LotteryConfigError as error:
        raise _config_http_error(error) from error
    return FileResponse(
        image.path,
        media_type=image.mime,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{activity_id}/lottery/prizes/{prize_id}/image")
def get_public_prize_image(
    activity_id: str,
    prize_id: int,
    version: Annotated[str, Query(alias="v", min_length=1, max_length=100)],
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        image = get_prize_image_file(activity_id, prize_id, version, settings)
    except LotteryConfigError as error:
        raise _config_http_error(error) from error
    return FileResponse(
        image.path,
        media_type=image.mime,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


@admin_router.get("/{activity_id}/lottery", response_model=LotteryConfigResponse)
def get_admin_lottery(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> LotteryConfigResponse:
    try:
        return get_lottery_config(activity_id, settings)
    except LotteryConfigError as error:
        raise _config_http_error(error) from error


@admin_router.post(
    "/{activity_id}/lottery/security-code/verify",
    response_model=LotterySecurityCodeResponse,
)
def verify_admin_lottery_security_code(
    activity_id: str,
    payload: LotterySecurityCodeRequest,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> LotterySecurityCodeResponse:
    try:
        verify_lottery_security_code(activity_id, payload.security_code, settings)
    except LotteryConfigError as error:
        raise _config_http_error(error) from error
    return LotterySecurityCodeResponse()


@admin_router.get("/{activity_id}/lottery/entries", response_model=LotteryEntryPage)
def get_admin_lottery_entries(
    activity_id: str,
    prize_id: Annotated[int, Query(ge=1)],
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[LotteryEntryStatus, Query(alias="status")] = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LotteryEntryPage:
    try:
        return get_lottery_entries(
            activity_id,
            prize_id,
            settings,
            keyword=keyword,
            status=status_filter,
            page=page,
            page_size=page_size,
        )
    except LotteryConfigError as error:
        raise _config_http_error(error) from error


@admin_router.put(
    "/{activity_id}/lottery/entries/{activity_user_id}",
    response_model=LotteryEntryUpdateResponse,
)
async def save_admin_lottery_entry(
    activity_id: str,
    activity_user_id: int,
    prize_id: Annotated[int, Query(ge=1)],
    payload: LotteryEntryUpdate,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> LotteryEntryUpdateResponse:
    async with lottery_operation_lock:
        if lottery_round_store.get(activity_id):
            raise _config_http_error(LotteryConfigError("draw_in_progress", "抽奖进行中，暂不能修改抽奖名单"))
        try:
            return await asyncio.to_thread(
                update_lottery_entry,
                activity_id,
                prize_id,
                activity_user_id,
                payload,
                settings,
            )
        except LotteryConfigError as error:
            raise _config_http_error(error) from error


@admin_router.put("/{activity_id}/lottery", response_model=LotteryConfigResponse)
async def save_admin_lottery(
    activity_id: str,
    payload: LotteryConfigUpdate,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> LotteryConfigResponse:
    async with lottery_operation_lock:
        if lottery_round_store.get(activity_id):
            raise _config_http_error(LotteryConfigError("draw_in_progress", "抽奖进行中，暂不能修改抽奖配置"))
        try:
            config = await asyncio.to_thread(update_lottery_config, activity_id, payload, settings)
        except LotteryConfigError as error:
            raise _config_http_error(error) from error
        await lottery_manager.broadcast(
            activity_id,
            {"type": "lottery.config.updated", "config": public_config(config)},
        )
    return config


@admin_router.get("/{activity_id}/lottery/history", response_model=LotteryHistoryPage)
def get_admin_lottery_history(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    before_id: Annotated[int | None, Query(ge=1)] = None,
) -> LotteryHistoryPage:
    try:
        return list_lottery_history(activity_id, settings, limit=limit, before_id=before_id)
    except LotteryConfigError as error:
        raise _config_http_error(error) from error


def _authenticate_admin_websocket(
    token: str,
    settings: Settings,
) -> str:
    try:
        payload = decode_access_token_payload(token, settings)
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员登录已失效") from error
    if payload.get("activity_id") is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能使用活动用户凭证连接管理端")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return require_superuser(credentials, settings)


async def _ready_payload(
    activity_id: str,
    settings: Settings,
    *,
    include_sensitive: bool,
) -> dict[str, object]:
    snapshot = await asyncio.to_thread(
        get_lottery_snapshot,
        activity_id,
        settings,
        include_sensitive=include_sensitive,
    )
    current = lottery_round_store.get(activity_id)
    return {
        "type": "lottery.ready",
        **snapshot,
        "selected_prize_id": current.prize_id if current else lottery_selection_store.get(activity_id),
        "active_round": current.public_payload() if current else None,
    }


@admin_router.websocket("/{activity_id}/lottery/ws")
async def admin_lottery_websocket(
    activity_id: str,
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
) -> None:
    await websocket.accept()
    connected = False
    try:
        try:
            raw_auth_message = await asyncio.wait_for(websocket.receive_text(), timeout=10)
            try:
                auth_message = loads(raw_auth_message)
            except JSONDecodeError:
                auth_message = raw_auth_message
        except asyncio.TimeoutError:
            await send_lottery_error(websocket, "unauthorized", "管理员连接需要首帧 JWT")
            await websocket.close(code=1008)
            return
        except WebSocketDisconnect:
            return
        except (JSONDecodeError, ValueError, TypeError):
            await send_lottery_error(websocket, "protocol_error", "首帧必须是合法 JSON")
            await websocket.close(code=1008)
            return
        token: str | None = None
        if isinstance(auth_message, str):
            token = auth_message
        elif isinstance(auth_message, dict) and auth_message.get("type") == "auth":
            value = auth_message.get("token")
            token = value if isinstance(value, str) else None
        if not token:
            await send_lottery_error(websocket, "unauthorized", "管理员连接需要有效 JWT")
            await websocket.close(code=1008)
            return
        try:
            await asyncio.to_thread(_authenticate_admin_websocket, token, settings)
            await lottery_manager.connect_and_send_ready(
                activity_id,
                websocket,
                "admin",
                lambda: _ready_payload(activity_id, settings, include_sensitive=True),
            )
        except HTTPException as error:
            await send_lottery_error(websocket, "unauthorized", str(error.detail))
            await websocket.close(code=1008)
            return
        except LotteryConfigError as error:
            await send_lottery_error(websocket, error.code, error.detail)
            await websocket.close(code=1008)
            return
        connected = True
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except (JSONDecodeError, ValueError, TypeError):
                await send_lottery_error(websocket, "protocol_error", "消息必须是合法 JSON")
                continue
            await handle_admin_lottery_message(activity_id, websocket, message, settings)
    finally:
        if connected:
            await lottery_manager.disconnect(activity_id, websocket)


@router.websocket("/{activity_id}/lottery/ws")
async def screen_lottery_websocket(
    activity_id: str,
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
) -> None:
    await websocket.accept()
    connected = False
    try:
        try:
            await lottery_manager.connect_and_send_ready(
                activity_id,
                websocket,
                "screen",
                lambda: _ready_payload(activity_id, settings, include_sensitive=False),
            )
        except LotteryConfigError as error:
            await send_lottery_error(websocket, error.code, error.detail)
            await websocket.close(code=1008)
            return
        connected = True
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except (JSONDecodeError, ValueError, TypeError):
                await send_lottery_error(websocket, "protocol_error", "消息必须是合法 JSON")
                continue
            if isinstance(message, dict) and message.get("type") in {"lottery.ping", "ping"}:
                await websocket.send_json({"type": "lottery.pong"})
            else:
                await send_lottery_error(websocket, "read_only", "大屏连接只允许读取抽奖状态")
    finally:
        if connected:
            await lottery_manager.disconnect(activity_id, websocket)
