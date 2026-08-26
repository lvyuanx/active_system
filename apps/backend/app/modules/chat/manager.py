import asyncio
from collections import defaultdict
from typing import Any

from starlette.websockets import WebSocket


class ChatConnectionManager:
    """进程内聊天室连接管理；多副本部署时由外部消息总线替换。"""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, activity_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms[activity_id].add(websocket)

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


chat_manager = ChatConnectionManager()
