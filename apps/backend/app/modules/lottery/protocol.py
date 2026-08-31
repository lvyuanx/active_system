import asyncio
from typing import Any

from fastapi import WebSocket

from app.core.config import Settings
from .manager import lottery_manager
from .round_state import LotteryRound, lottery_round_store
from .service import (
    LotteryConfigError,
    LotteryDrawError,
    draw_lottery,
    prepare_lottery_round,
    reset_lottery,
)
from .snapshot import public_snapshot
from .state import lottery_operation_lock


async def send_lottery_error(
    websocket: WebSocket,
    code: str,
    detail: str,
    *,
    request_id: str | None = None,
    round_id: str | None = None,
) -> None:
    payload: dict[str, object] = {"type": "lottery.draw.error", "code": code, "detail": detail}
    if request_id:
        payload["request_id"] = request_id
    if round_id:
        payload["round_id"] = round_id
    await websocket.send_json(payload)


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _round_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value and len(value) <= 100 else None


def _started_payload(lottery_round: LotteryRound) -> dict[str, Any]:
    return {"type": "lottery.draw.started", "round": lottery_round.public_payload()}


def _stopping_payload(lottery_round: LotteryRound) -> dict[str, Any]:
    return {
        "type": "lottery.draw.stopping",
        "request_id": lottery_round.round_id,
        "round_id": lottery_round.round_id,
    }


def _draw_result_payload(round_id: str, outcome: Any) -> dict[str, Any]:
    return {
        "type": "lottery.draw.result",
        "request_id": round_id,
        "round_id": round_id,
        "idempotent": outcome.idempotent,
        "draw": outcome.draw.model_dump(mode="json"),
    }


async def _handle_start(
    activity_id: str,
    websocket: WebSocket,
    message: dict[str, object],
    settings: Settings,
) -> None:
    round_id = _round_id(message.get("round_id"))
    prize_id = _positive_int(message.get("prize_id"))
    if round_id is None or prize_id is None:
        await send_lottery_error(websocket, "invalid_request", "round_id 和 prize_id 参数无效")
        return
    async with lottery_operation_lock:
        current = lottery_round_store.get(activity_id)
        if current:
            if current.round_id == round_id and current.prize_id == prize_id:
                if current.phase == "stopping":
                    await lottery_manager.send(websocket, _stopping_payload(current))
                else:
                    await lottery_manager.send(websocket, _started_payload(current))
            else:
                await send_lottery_error(
                    websocket,
                    "draw_in_progress",
                    "当前活动已有抽奖正在进行",
                    round_id=round_id,
                )
            return
        try:
            lottery_round = await asyncio.to_thread(
                prepare_lottery_round,
                activity_id,
                prize_id,
                round_id,
                settings,
            )
        except LotteryDrawError as error:
            await send_lottery_error(websocket, error.code, error.detail, round_id=round_id)
            return
        if not lottery_round_store.put_if_absent(lottery_round):
            await send_lottery_error(websocket, "draw_in_progress", "当前活动已有抽奖正在进行", round_id=round_id)
            return
        await lottery_manager.broadcast(activity_id, _started_payload(lottery_round))


async def _handle_stop(
    activity_id: str,
    websocket: WebSocket,
    message: dict[str, object],
    settings: Settings,
) -> None:
    round_id = _round_id(message.get("round_id"))
    prize_id = _positive_int(message.get("prize_id"))
    if round_id is None or prize_id is None:
        await send_lottery_error(websocket, "invalid_request", "round_id 和 prize_id 参数无效")
        return
    async with lottery_operation_lock:
        current = lottery_round_store.get(activity_id)
        if current and current.round_id != round_id:
            await send_lottery_error(websocket, "draw_in_progress", "当前活动正在进行其他抽奖", round_id=round_id)
            return
        if current and current.prize_id != prize_id:
            await send_lottery_error(websocket, "request_conflict", "抽奖轮次与奖品不匹配", round_id=round_id)
            return
        if current:
            stopping_round = lottery_round_store.mark_stopping(activity_id, round_id)
            if stopping_round:
                await lottery_manager.broadcast(activity_id, _stopping_payload(stopping_round))
        try:
            outcome = await asyncio.to_thread(
                draw_lottery,
                activity_id,
                prize_id,
                round_id,
                settings,
                candidate_user_ids=current.candidate_user_ids if current else None,
                existing_only=current is None,
            )
        except LotteryDrawError as error:
            if current:
                lottery_round_store.clear_if(activity_id, round_id)
                await lottery_manager.broadcast(
                    activity_id,
                    {
                        "type": "lottery.draw.error",
                        "code": error.code,
                        "detail": error.detail,
                        "request_id": round_id,
                        "round_id": round_id,
                    },
                )
            else:
                await send_lottery_error(websocket, error.code, error.detail, round_id=round_id)
            return
        result = _draw_result_payload(round_id, outcome)
        if outcome.idempotent:
            lottery_round_store.clear_if(activity_id, round_id)
            await lottery_manager.send(websocket, result)
            return
        lottery_round_store.clear_if(activity_id, round_id)
        await lottery_manager.broadcast_role(activity_id, "admin", result)
        await lottery_manager.broadcast_role(
            activity_id,
            "screen",
            {
                "type": "lottery.drawn",
                "round_id": round_id,
                "draw": outcome.public_draw.model_dump(mode="json"),
                "roll_names": outcome.roll_names,
            },
        )


async def _handle_legacy_draw(
    activity_id: str,
    websocket: WebSocket,
    message: dict[str, object],
    settings: Settings,
) -> None:
    prize_id = _positive_int(message.get("prize_id"))
    request_id = message.get("request_id")
    if prize_id is None or not isinstance(request_id, str) or not request_id.strip() or len(request_id.strip()) > 100:
        await send_lottery_error(websocket, "invalid_request", "prize_id 或 request_id 参数无效")
        return
    request_id = request_id.strip()
    async with lottery_operation_lock:
        if lottery_round_store.get(activity_id):
            await send_lottery_error(websocket, "draw_in_progress", "请先完成当前抽奖轮次", request_id=request_id)
            return
        try:
            outcome = await asyncio.to_thread(
                draw_lottery,
                activity_id,
                prize_id,
                request_id,
                settings,
            )
        except LotteryDrawError as error:
            await send_lottery_error(websocket, error.code, error.detail, request_id=request_id)
            return
        result = _draw_result_payload(request_id, outcome)
        if outcome.idempotent:
            await lottery_manager.send(websocket, result)
            return
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


async def _handle_reset(
    activity_id: str,
    websocket: WebSocket,
    settings: Settings,
) -> None:
    async with lottery_operation_lock:
        if lottery_round_store.get(activity_id):
            await send_lottery_error(websocket, "draw_in_progress", "抽奖进行中，暂不能重置")
            return
        try:
            snapshot = await asyncio.to_thread(reset_lottery, activity_id, settings)
        except LotteryConfigError as error:
            await send_lottery_error(websocket, error.code, error.detail)
            return
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


async def handle_admin_lottery_message(
    activity_id: str,
    websocket: WebSocket,
    message: object,
    settings: Settings,
) -> None:
    if not isinstance(message, dict):
        await send_lottery_error(websocket, "protocol_error", "消息格式不正确")
        return
    message_type = message.get("type")
    if message_type in {"lottery.ping", "ping"}:
        await websocket.send_json({"type": "lottery.pong"})
    elif message_type == "lottery.draw.start":
        await _handle_start(activity_id, websocket, message, settings)
    elif message_type == "lottery.draw.stop":
        await _handle_stop(activity_id, websocket, message, settings)
    elif message_type == "lottery.draw.request":
        await _handle_legacy_draw(activity_id, websocket, message, settings)
    elif message_type in {"lottery.reset.request", "lottery.reset"}:
        await _handle_reset(activity_id, websocket, settings)
    else:
        await send_lottery_error(websocket, "protocol_error", "不支持的消息类型")


__all__ = ["handle_admin_lottery_message", "send_lottery_error"]
