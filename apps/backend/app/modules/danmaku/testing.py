import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.config import Settings
from app.core.database import transaction
from app.modules.chat.manager import chat_manager
from app.modules.chat.service import ChatReadOnlyError, create_message
from app.modules.danmaku.manager import danmaku_manager
from app.modules.participants.router import ActivityPrincipal


TEST_USER_COUNT = 6
TEST_INTERVAL_SECONDS = 0.85
TEST_MESSAGES = (
    "【弹幕测试】欢迎来到活动现场！",
    "【弹幕测试】这个设置效果很不错",
    "【弹幕测试】正在模拟多位用户发言",
    "【弹幕测试】支持轨道、字号和颜色实时调整",
    "【弹幕测试】现场气氛拉满！",
    "【弹幕测试】这是一条真实聊天室测试消息",
)


@dataclass(frozen=True)
class TestUser:
    activity_user_id: int
    username: str
    joined_at: datetime


def _test_username(index: int) -> str:
    return f"弹幕测试用户{index + 1}"


def _test_phone(activity_id: str, index: int) -> str:
    compact_id = activity_id.replace("-", "")[:16]
    return f"dmtest-{compact_id}-{index + 1}"


def ensure_test_users(activity_id: str, settings: Settings) -> list[TestUser]:
    now = datetime.now(timezone.utc).isoformat()
    with transaction(settings) as connection:
        activity = connection.execute(
            "SELECT status FROM activities WHERE activity_id = ?", (activity_id,)
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
        if activity["status"] != "open":
            raise ChatReadOnlyError
        users: list[TestUser] = []
        for index in range(TEST_USER_COUNT):
            username = _test_username(index)
            phone = _test_phone(activity_id, index)
            row = connection.execute(
                "SELECT id, username, created_at FROM activity_users "
                "WHERE activity_id = ? AND phone = ? LIMIT 1",
                (activity_id, phone),
            ).fetchone()
            if not row:
                connection.execute(
                    "INSERT OR IGNORE INTO activity_users("
                    "activity_id, username, phone, created_at, avatar_id) VALUES (?, ?, ?, ?, ?)",
                    (activity_id, username, phone, now, index + 1),
                )
                row = connection.execute(
                    "SELECT id, username, created_at FROM activity_users "
                    "WHERE activity_id = ? AND phone = ? LIMIT 1",
                    (activity_id, phone),
                ).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="测试用户创建失败")
            if row["username"] != username:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="测试用户标识发生冲突")
            users.append(
                TestUser(
                    activity_user_id=int(row["id"]),
                    username=str(row["username"]),
                    joined_at=datetime.fromisoformat(str(row["created_at"])),
                )
            )
    return users


class DanmakuTestManager:
    def __init__(self, interval_seconds: float = TEST_INTERVAL_SECONDS) -> None:
        self.interval_seconds = interval_seconds
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def start(self, activity_id: str, settings: Settings) -> bool:
        async with self._lock:
            current = self._tasks.get(activity_id)
            if current and not current.done():
                return False
            users = await asyncio.to_thread(ensure_test_users, activity_id, settings)
            task = asyncio.create_task(self._run(activity_id, users, settings))
            self._tasks[activity_id] = task
        return True

    async def stop(self, activity_id: str) -> bool:
        async with self._lock:
            task = self._tasks.pop(activity_id, None)
        if not task:
            return False
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return True

    def is_running(self, activity_id: str) -> bool:
        task = self._tasks.get(activity_id)
        return bool(task and not task.done())

    async def stop_all(self) -> None:
        async with self._lock:
            tasks = list(self._tasks.values())
            self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, activity_id: str, users: list[TestUser], settings: Settings) -> None:
        message_index = 0
        try:
            while True:
                user = users[message_index % len(users)]
                principal = ActivityPrincipal(
                    activity_id=activity_id,
                    activity_user_id=user.activity_user_id,
                    username=user.username,
                    joined_at=user.joined_at,
                )
                try:
                    created = await asyncio.to_thread(
                        create_message,
                        activity_id,
                        principal,
                        TEST_MESSAGES[message_index % len(TEST_MESSAGES)],
                        settings,
                    )
                except (ChatReadOnlyError, HTTPException, ValueError):
                    return
                message = created.model_dump(mode="json")
                await chat_manager.broadcast(
                    activity_id, {"type": "message.created", "message": message}
                )
                await danmaku_manager.broadcast_message(activity_id, message)
                message_index += 1
                await asyncio.sleep(self.interval_seconds)
        finally:
            current = asyncio.current_task()
            async with self._lock:
                if self._tasks.get(activity_id) is current:
                    self._tasks.pop(activity_id, None)


danmaku_test_manager = DanmakuTestManager()
