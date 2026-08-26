from datetime import datetime, timezone
import sqlite3

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.database import transaction
from app.modules.participants.router import ActivityPrincipal


class ChatMessage(BaseModel):
    message_id: int
    activity_id: str
    sender_activity_user_id: int
    sender_username: str
    body: str
    created_at: datetime


class ChatMessagePage(BaseModel):
    items: list[ChatMessage]
    has_more: bool


class ChatMessageInput(BaseModel):
    body: str = Field(min_length=1, max_length=500)


class ChatReadOnlyError(Exception):
    pass


def _message_from_row(row: sqlite3.Row) -> ChatMessage:
    return ChatMessage(
        message_id=int(row["message_id"]),
        activity_id=str(row["activity_id"]),
        sender_activity_user_id=int(row["activity_user_id"]),
        sender_username=str(row["username"]),
        body=str(row["body"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def list_messages(
    activity_id: str,
    principal: ActivityPrincipal,
    settings: Settings,
    *,
    limit: int = 50,
    before_id: int | None = None,
    after_id: int | None = None,
) -> ChatMessagePage:
    if principal.activity_id != activity_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能访问其他活动")
    if before_id is not None and after_id is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="游标参数不能同时使用")
    with transaction(settings) as connection:
        if before_id is not None:
            rows = connection.execute(
                "SELECT m.*, u.username FROM activity_chat_messages m "
                "JOIN activity_users u ON u.id = m.activity_user_id "
                "WHERE m.activity_id = ? AND m.message_id < ? "
                "ORDER BY m.message_id DESC LIMIT ?",
                (activity_id, before_id, limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = list(reversed(rows[:limit]))
        elif after_id is not None:
            rows = connection.execute(
                "SELECT m.*, u.username FROM activity_chat_messages m "
                "JOIN activity_users u ON u.id = m.activity_user_id "
                "WHERE m.activity_id = ? AND m.message_id > ? "
                "ORDER BY m.message_id ASC LIMIT ?",
                (activity_id, after_id, limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = rows[:limit]
        else:
            rows = connection.execute(
                "SELECT m.*, u.username FROM activity_chat_messages m "
                "JOIN activity_users u ON u.id = m.activity_user_id "
                "WHERE m.activity_id = ? ORDER BY m.message_id DESC LIMIT ?",
                (activity_id, limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = list(reversed(rows[:limit]))
    return ChatMessagePage(items=[_message_from_row(row) for row in rows], has_more=has_more)


def create_message(
    activity_id: str,
    principal: ActivityPrincipal,
    body: str,
    settings: Settings,
) -> ChatMessage:
    body = body.strip()
    if not 1 <= len(body) <= 500:
        raise ValueError("消息长度必须为 1 至 500 个字符")
    with transaction(settings) as connection:
        activity = connection.execute(
            "SELECT status FROM activities WHERE activity_id = ?", (activity_id,)
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
        if activity["status"] != "open":
            raise ChatReadOnlyError
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "INSERT INTO activity_chat_messages(activity_id, activity_user_id, body, created_at) "
            "VALUES (?, ?, ?, ?)",
            (activity_id, principal.activity_user_id, body, now),
        )
        row = connection.execute(
            "SELECT m.*, u.username FROM activity_chat_messages m "
            "JOIN activity_users u ON u.id = m.activity_user_id WHERE m.message_id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _message_from_row(row)
