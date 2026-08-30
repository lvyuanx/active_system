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
    LotteryDrawError,
    LotteryHistoryPage,
    draw_lottery,
    get_lottery_entries,
    get_lottery_config,
    get_lottery_snapshot,
    list_lottery_history,
    public_config,
    public_snapshot,
    reset_lottery,
    update_lottery_entry,
    update_lottery_config,
)


admin_router = APIRouter(prefix="/admin/activities", tags=["lottery-admin"])
router = APIRouter(prefix="/activities", tags=["lottery"])
lottery_operation_lock = asyncio.Lock()


def _config_http_error(error: LotteryConfigError) -> HTTPException:
    if error.code in {
        "activity_not_found",
        "entry_not_found",
        "invalid_prize",
        "image_not_found",
    }:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.detail)
    if error.code in {"config_conflict", "prize_has_draws", "quantity_below_draws"}:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail)
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


@admin_router.get("/{activity_id}/lottery/entries", response_model=LotteryEntryPage)
def get_admin_lottery_entries(
    activity_id: str,
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
def save_admin_lottery_entry(
    activity_id: str,
    activity_user_id: int,
    payload: LotteryEntryUpdate,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> LotteryEntryUpdateResponse:
    try:
        return update_lottery_entry(activity_id, activity_user_id, payload, settings)
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


async def _send_error(
    websocket: WebSocket,
    code: str,
    detail: str,
    *,
    request_id: str | None = None,
) -> None:
    payload: dict[str, object] = {"type": "lottery.draw.error", "code": code, "detail": detail}
    if request_id:
        payload["request_id"] = request_id
    await websocket.send_json(payload)


def _ready_payload(snapshot: dict[str, object]) -> dict[str, object]:
    return {"type": "lottery.ready", **snapshot}


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
            await _send_error(websocket, "unauthorized", "管理员连接需要首帧 JWT")
            await websocket.close(code=1008)
            return
        except WebSocketDisconnect:
            return
        except (JSONDecodeError, ValueError, TypeError):
            await _send_error(websocket, "protocol_error", "首帧必须是合法 JSON")
            await websocket.close(code=1008)
            return
        token: str | None = None
        if isinstance(auth_message, str):
            token = auth_message
        elif isinstance(auth_message, dict) and auth_message.get("type") == "auth":
            value = auth_message.get("token")
            token = value if isinstance(value, str) else None
        if not token:
            await _send_error(websocket, "unauthorized", "管理员连接需要有效 JWT")
            await websocket.close(code=1008)
            return
        try:
            await asyncio.to_thread(_authenticate_admin_websocket, token, settings)
            snapshot = await asyncio.to_thread(
                get_lottery_snapshot,
                activity_id,
                settings,
                include_sensitive=True,
            )
        except HTTPException as error:
            await _send_error(websocket, "unauthorized", str(error.detail))
            await websocket.close(code=1008)
            return
        except LotteryConfigError as error:
            await _send_error(websocket, error.code, error.detail)
            await websocket.close(code=1008)
            return
        await lottery_manager.connect_and_send_ready(
            activity_id,
            websocket,
            "admin",
            _ready_payload(snapshot),
        )
        connected = True
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except (JSONDecodeError, ValueError, TypeError):
                await _send_error(websocket, "protocol_error", "消息必须是合法 JSON")
                continue
            if not isinstance(message, dict):
                await _send_error(websocket, "protocol_error", "消息格式不正确")
                continue
            message_type = message.get("type")
            if message_type in {"lottery.ping", "ping"}:
                await websocket.send_json({"type": "lottery.pong"})
                continue
            if message_type == "lottery.draw.request":
                prize_id = message.get("prize_id")
                request_id = message.get("request_id")
                if isinstance(prize_id, bool) or not isinstance(prize_id, int) or prize_id < 1:
                    await _send_error(websocket, "invalid_request", "prize_id 必须是正整数")
                    continue
                if not isinstance(request_id, str) or not request_id.strip() or len(request_id.strip()) > 100:
                    await _send_error(websocket, "invalid_request", "request_id 必须是 1 至 100 个字符")
                    continue
                async with lottery_operation_lock:
                    try:
                        outcome = await asyncio.to_thread(
                            draw_lottery,
                            activity_id,
                            prize_id,
                            request_id,
                            settings,
                        )
                    except LotteryDrawError as error:
                        await _send_error(websocket, error.code, error.detail, request_id=request_id)
                        continue
                    result = {
                        "type": "lottery.draw.result",
                        "request_id": request_id,
                        "idempotent": outcome.idempotent,
                        "draw": outcome.draw.model_dump(mode="json"),
                    }
                    if outcome.idempotent:
                        await websocket.send_json(result)
                        continue
                    await lottery_manager.broadcast_role(activity_id, "admin", result)
                    await lottery_manager.broadcast_role(
                        activity_id,
                        "screen",
                        {
                            "type": "lottery.drawn",
                            "draw": outcome.public_draw.model_dump(mode="json"),
                            "roll_names": outcome.roll_names,
                        },
                    )
                continue
            if message_type in {"lottery.reset.request", "lottery.reset"}:
                async with lottery_operation_lock:
                    try:
                        snapshot = await asyncio.to_thread(reset_lottery, activity_id, settings)
                    except LotteryConfigError as error:
                        await _send_error(websocket, error.code, error.detail)
                        continue
                    await lottery_manager.broadcast_role(
                        activity_id,
                        "admin",
                        {"type": "lottery.reset", "snapshot": snapshot},
                    )
                    await lottery_manager.broadcast_role(
                        activity_id,
                        "screen",
                        {"type": "lottery.reset", "snapshot": public_snapshot(snapshot)},
                    )
                continue
            await _send_error(websocket, "protocol_error", "不支持的消息类型")
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
            snapshot = await asyncio.to_thread(
                get_lottery_snapshot,
                activity_id,
                settings,
                include_sensitive=False,
            )
        except LotteryConfigError as error:
            await _send_error(websocket, error.code, error.detail)
            await websocket.close(code=1008)
            return
        await lottery_manager.connect_and_send_ready(
            activity_id,
            websocket,
            "screen",
            _ready_payload(snapshot),
        )
        connected = True
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except (JSONDecodeError, ValueError, TypeError):
                await _send_error(websocket, "protocol_error", "消息必须是合法 JSON")
                continue
            if isinstance(message, dict) and message.get("type") in {"lottery.ping", "ping"}:
                await websocket.send_json({"type": "lottery.pong"})
            else:
                await _send_error(websocket, "read_only", "大屏连接只允许读取抽奖状态")
    finally:
        if connected:
            await lottery_manager.disconnect(activity_id, websocket)
