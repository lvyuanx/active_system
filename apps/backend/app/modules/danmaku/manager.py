import asyncio
from collections import defaultdict
from contextlib import suppress
from typing import Any

from starlette.websockets import WebSocket


class DanmakuConnectionManager:
    """维护活动级弹幕监听连接，不持有参与者身份或聊天写权限。"""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._minimum_token_versions: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def connect(self, activity_id: str, websocket: WebSocket, token_version: int) -> bool:
        async with self._lock:
            if token_version < self._minimum_token_versions.get(activity_id, 0):
                return False
            self._rooms[activity_id].add(websocket)
        return True

    async def disconnect(self, activity_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(activity_id)
            if room is None:
                return
            room.discard(websocket)
            if not room:
                self._rooms.pop(activity_id, None)

    async def broadcast(self, activity_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            recipients = tuple(self._rooms.get(activity_id, ()))
        failed: list[WebSocket] = []
        for websocket in recipients:
            try:
                await websocket.send_json(payload)
            except Exception:
                failed.append(websocket)
        for websocket in failed:
            await self.disconnect(activity_id, websocket)

    async def broadcast_message(self, activity_id: str, message: dict[str, Any]) -> None:
        summary = {
            key: message[key]
            for key in ("message_id", "activity_id", "body", "created_at")
            if key in message
        }
        await self.broadcast(
            activity_id,
            {"type": "danmaku.message.created", "message": summary},
        )

    async def invalidate_activity(self, activity_id: str, token_version: int) -> None:
        async with self._lock:
            self._minimum_token_versions[activity_id] = max(
                token_version,
                self._minimum_token_versions.get(activity_id, 0),
            )
            recipients = tuple(self._rooms.pop(activity_id, ()))
        for websocket in recipients:
            with suppress(Exception):
                await websocket.close(code=4001, reason="弹幕 token 已更新")


danmaku_manager = DanmakuConnectionManager()
