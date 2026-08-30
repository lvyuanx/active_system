import asyncio
from collections import defaultdict
from typing import Any, Literal

from starlette.websockets import WebSocket


LotteryRole = Literal["admin", "screen"]


class LotteryConnectionManager:
    """维护活动级抽奖连接；多副本部署时由共享消息总线替换。"""

    def __init__(self) -> None:
        self._rooms: dict[str, dict[WebSocket, LotteryRole]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._broadcast_lock = asyncio.Lock()

    async def connect(self, activity_id: str, websocket: WebSocket, role: LotteryRole) -> None:
        async with self._lock:
            self._rooms[activity_id][websocket] = role

    async def connect_and_send_ready(
        self,
        activity_id: str,
        websocket: WebSocket,
        role: LotteryRole,
        payload: dict[str, Any],
    ) -> None:
        """在广播屏障内注册连接并发送首帧，避免事件插入 ready 之前。"""
        async with self._broadcast_lock:
            await self.connect(activity_id, websocket, role)
            try:
                await websocket.send_json(payload)
            except Exception:
                await self._remove_socket(websocket)
                raise

    async def disconnect(self, activity_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(activity_id)
            if room is None:
                return
            room.pop(websocket, None)
            if not room:
                self._rooms.pop(activity_id, None)

    async def send(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            await self._remove_socket(websocket)

    async def broadcast_role(
        self,
        activity_id: str,
        role: LotteryRole,
        payload: dict[str, Any],
    ) -> None:
        async with self._broadcast_lock:
            async with self._lock:
                recipients = tuple(
                    websocket
                    for websocket, recipient_role in self._rooms.get(activity_id, {}).items()
                    if recipient_role == role
                )
            failed: list[WebSocket] = []
            for websocket in recipients:
                try:
                    await websocket.send_json(payload)
                except Exception:
                    failed.append(websocket)
            for websocket in failed:
                await self._remove_socket(websocket)

    async def broadcast(self, activity_id: str, payload: dict[str, Any]) -> None:
        async with self._broadcast_lock:
            async with self._lock:
                recipients = tuple(self._rooms.get(activity_id, {}).keys())
            failed: list[WebSocket] = []
            for websocket in recipients:
                try:
                    await websocket.send_json(payload)
                except Exception:
                    failed.append(websocket)
            for websocket in failed:
                await self._remove_socket(websocket)

    async def _remove_socket(self, websocket: WebSocket) -> None:
        async with self._lock:
            empty_rooms: list[str] = []
            for activity_id, room in self._rooms.items():
                room.pop(websocket, None)
                if not room:
                    empty_rooms.append(activity_id)
            for activity_id in empty_rooms:
                self._rooms.pop(activity_id, None)


lottery_manager = LotteryConnectionManager()
