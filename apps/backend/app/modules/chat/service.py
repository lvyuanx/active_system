from datetime import datetime, timezone
import sqlite3
from typing import Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.database import transaction
from app.modules.participants.router import ActivityPrincipal
from app.modules.chat.stickers import ChatSticker, sticker_from_message_row


class ChatMessage(BaseModel):
    message_id: int
    activity_id: str
    sender_activity_user_id: int
    sender_username: str
    body: str
    created_at: datetime
    message_type: Literal["text", "sticker"] = "text"
    sticker: ChatSticker | None = None


class ChatMessagePage(BaseModel):
    items: list[ChatMessage]
    has_more: bool


class ChatMessageInput(BaseModel):
    body: str = Field(min_length=1, max_length=500)


class ChatReadOnlyError(Exception):
    pass


class ChatMutedError(Exception):
    pass


class ChatParticipantInactiveError(Exception):
    pass


class ChatInvalidStickerError(Exception):
    pass


def _message_select() -> str:
    return (
        "SELECT m.*, u.username, s.name AS sticker_name, s.image_id AS sticker_image_id, "
        "s.image_mime AS sticker_image_mime, s.image_width AS sticker_image_width, "
        "s.image_height AS sticker_image_height "
        "FROM activity_chat_messages m "
        "JOIN activity_users u ON u.id = m.activity_user_id "
        "LEFT JOIN activity_chat_stickers s "
        "ON s.sticker_id = m.sticker_id AND s.activity_id = m.activity_id "
    )


def _message_from_row(row: sqlite3.Row) -> ChatMessage:
    message_type = str(row["message_type"] or "text")
    return ChatMessage(
        message_id=int(row["message_id"]),
        activity_id=str(row["activity_id"]),
        sender_activity_user_id=int(row["activity_user_id"]),
        sender_username=str(row["username"]),
        body=str(row["body"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        message_type=message_type if message_type in {"text", "sticker"} else "text",
        sticker=sticker_from_message_row(row) if message_type == "sticker" else None,
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
                _message_select()
                + "WHERE m.activity_id = ? AND m.message_id < ? "
                "ORDER BY m.message_id DESC LIMIT ?",
                (activity_id, before_id, limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = list(reversed(rows[:limit]))
        elif after_id is not None:
            rows = connection.execute(
                _message_select()
                + "WHERE m.activity_id = ? AND m.message_id > ? "
                "ORDER BY m.message_id ASC LIMIT ?",
                (activity_id, after_id, limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = rows[:limit]
        else:
            rows = connection.execute(
                _message_select()
                + "WHERE m.activity_id = ? ORDER BY m.message_id DESC LIMIT ?",
                (activity_id, limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = list(reversed(rows[:limit]))
    return ChatMessagePage(items=[_message_from_row(row) for row in rows], has_more=has_more)


def create_message(
    activity_id: str,
    principal: ActivityPrincipal,
    body: str | None,
    settings: Settings,
    *,
    sticker_id: int | None = None,
) -> ChatMessage:
    if sticker_id is not None:
        if (
            body is not None
            or isinstance(sticker_id, bool)
            or not isinstance(sticker_id, int)
            or sticker_id < 1
        ):
            raise ChatInvalidStickerError
        normalized_body: str | None = None
    else:
        if not isinstance(body, str):
            raise ValueError("消息正文必须是文本")
        normalized_body = body.strip()
        if not 1 <= len(normalized_body) <= 500:
            raise ValueError("消息长度必须为 1 至 500 个字符")
    if principal.activity_id != activity_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能访问其他活动")
    with transaction(settings) as connection:
        activity = connection.execute(
            "SELECT status FROM activities WHERE activity_id = ?", (activity_id,)
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
        participant = connection.execute(
            "SELECT is_active, is_muted FROM activity_users WHERE activity_id = ? AND id = ?",
            (activity_id, principal.activity_user_id),
        ).fetchone()
        if not participant or not bool(participant["is_active"]):
            raise ChatParticipantInactiveError
        if activity["status"] != "open":
            raise ChatReadOnlyError
        if bool(participant["is_muted"]):
            raise ChatMutedError
        sticker = None
        if sticker_id is not None:
            sticker = connection.execute(
                """SELECT sticker_id, name FROM activity_chat_stickers
                   WHERE activity_id = ? AND sticker_id = ? AND is_enabled = 1""",
                (activity_id, sticker_id),
            ).fetchone()
            if not sticker:
                raise ChatInvalidStickerError
            normalized_body = f"[表情] {sticker['name']}"
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            """INSERT INTO activity_chat_messages(
                activity_id, activity_user_id, body, created_at, message_type, sticker_id
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                activity_id,
                principal.activity_user_id,
                normalized_body,
                now,
                "sticker" if sticker_id is not None else "text",
                sticker_id,
            ),
        )
        row = connection.execute(
            _message_select() + "WHERE m.message_id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        if not row:
            raise RuntimeError("聊天消息创建失败")
    return _message_from_row(row)
