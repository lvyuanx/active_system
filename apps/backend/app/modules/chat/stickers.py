"""活动聊天表情库、媒体绑定和版本化公开图片服务。"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
from urllib.parse import quote

from fastapi import HTTPException, status
from fastapi import UploadFile
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.database import transaction
from app.modules.files.service import (
    CHAT_STICKERS_NAMESPACE,
    MediaError,
    StoredMedia,
    remove_storage_key,
    scan_orphan_files,
    storage_path,
    store_uploaded_image,
)


logger = logging.getLogger(__name__)


class ChatSticker(BaseModel):
    sticker_id: int
    name: str
    image_url: str
    mime: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ChatStickerAdminResponse(ChatSticker):
    activity_id: str
    image_id: str
    size: int = Field(gt=0)
    is_enabled: bool
    created_at: datetime


class ChatStickerError(Exception):
    """可安全映射到 HTTP 响应的表情业务错误。"""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class ChatStickerFile:
    image_id: str
    mime: str
    path: Path


def sticker_image_url(activity_id: str, sticker_id: int, image_id: str) -> str:
    safe_activity_id = quote(activity_id, safe="")
    safe_image_id = quote(image_id, safe="")
    return (
        f"/api/v1/activities/{safe_activity_id}/chat/stickers/{sticker_id}/image"
        f"?v={safe_image_id}"
    )


def _select_sticker_row(connection: sqlite3.Connection, activity_id: str, sticker_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """SELECT sticker_id, activity_id, name, image_id, image_storage_key, image_mime, image_size,
                  image_width, image_height, is_enabled, created_at
           FROM activity_chat_stickers
           WHERE activity_id = ? AND sticker_id = ?""",
        (activity_id, sticker_id),
    ).fetchone()


def _require_activity(connection: sqlite3.Connection, activity_id: str) -> None:
    if not connection.execute(
        "SELECT activity_id FROM activities WHERE activity_id = ?", (activity_id,)
    ).fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")


def _require_sticker(connection: sqlite3.Connection, activity_id: str, sticker_id: int) -> sqlite3.Row:
    row = _select_sticker_row(connection, activity_id, sticker_id)
    if not row:
        raise ChatStickerError("sticker_not_found", "表情不存在或不属于当前活动")
    return row


def _sticker_from_row(row: sqlite3.Row, *, public: bool = True) -> ChatSticker | ChatStickerAdminResponse:
    image_id = str(row["image_id"])
    common = {
        "sticker_id": int(row["sticker_id"]),
        "name": str(row["name"]),
        "image_url": sticker_image_url(str(row["activity_id"]), int(row["sticker_id"]), image_id),
        "mime": str(row["image_mime"]),
        "width": int(row["image_width"]),
        "height": int(row["image_height"]),
    }
    if public:
        return ChatSticker(**common)
    return ChatStickerAdminResponse(
        **common,
        activity_id=str(row["activity_id"]),
        image_id=image_id,
        size=int(row["image_size"]),
        is_enabled=bool(row["is_enabled"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def sticker_from_message_row(row: sqlite3.Row) -> ChatSticker | None:
    """从消息查询的左连接字段构造历史表情，允许表情已软下架。"""

    fields = (
        row["sticker_id"],
        row["sticker_name"],
        row["sticker_image_id"],
        row["sticker_image_mime"],
        row["sticker_image_width"],
        row["sticker_image_height"],
    )
    if any(value is None for value in fields):
        return None
    return ChatSticker(
        sticker_id=int(row["sticker_id"]),
        name=str(row["sticker_name"]),
        image_url=sticker_image_url(
            str(row["activity_id"]),
            int(row["sticker_id"]),
            str(row["sticker_image_id"]),
        ),
        mime=str(row["sticker_image_mime"]),
        width=int(row["sticker_image_width"]),
        height=int(row["sticker_image_height"]),
    )


def list_stickers(
    activity_id: str,
    settings: Settings,
    *,
    enabled_only: bool,
) -> list[ChatSticker | ChatStickerAdminResponse]:
    with transaction(settings) as connection:
        _require_activity(connection, activity_id)
        enabled_clause = " AND is_enabled = 1" if enabled_only else ""
        rows = connection.execute(
            "SELECT sticker_id, activity_id, name, image_id, image_storage_key, image_mime, image_size, "
            "image_width, image_height, is_enabled, created_at "
            f"FROM activity_chat_stickers WHERE activity_id = ?{enabled_clause} ORDER BY sticker_id ASC",
            (activity_id,),
        ).fetchall()
    return [_sticker_from_row(row, public=enabled_only) for row in rows]


def _default_sticker_name(filename: str) -> str:
    return Path(filename).stem.strip()


async def create_sticker(
    activity_id: str,
    upload: UploadFile,
    settings: Settings,
    name: str | None = None,
) -> ChatStickerAdminResponse:
    with transaction(settings) as connection:
        _require_activity(connection, activity_id)
    sticker_name = (name or "").strip() or _default_sticker_name(upload.filename or "")
    if not 1 <= len(sticker_name) <= 100:
        raise ChatStickerError("invalid_name", "表情名称长度必须为 1 至 100 个字符")

    stored = await store_uploaded_image(upload, settings, namespace=CHAT_STICKERS_NAMESPACE)
    try:
        now = datetime.now(timezone.utc).isoformat()
        with transaction(settings) as connection:
            connection.execute("BEGIN IMMEDIATE")
            _require_activity(connection, activity_id)
            cursor = connection.execute(
                """INSERT INTO activity_chat_stickers(
                    activity_id, name, image_id, image_storage_key, image_mime, image_size,
                    image_width, image_height, is_enabled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    activity_id,
                    sticker_name,
                    stored.image_id,
                    stored.storage_key,
                    stored.mime,
                    stored.size,
                    stored.width,
                    stored.height,
                    now,
                ),
            )
            row = _select_sticker_row(connection, activity_id, int(cursor.lastrowid))
            if not row:
                raise ChatStickerError("sticker_create_failed", "表情创建失败")
    except Exception:
        remove_storage_key(settings, stored.storage_key, namespace=CHAT_STICKERS_NAMESPACE)
        raise
    scan_chat_sticker_media(settings)
    return _sticker_from_row(row, public=False)  # type: ignore[return-value]


def set_sticker_enabled(
    activity_id: str,
    sticker_id: int,
    settings: Settings,
    *,
    enabled: bool,
) -> ChatStickerAdminResponse:
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _require_sticker(connection, activity_id, sticker_id)
        connection.execute(
            "UPDATE activity_chat_stickers SET is_enabled = ? WHERE activity_id = ? AND sticker_id = ?",
            (int(enabled), activity_id, sticker_id),
        )
        updated = _select_sticker_row(connection, activity_id, sticker_id)
        if not updated:
            raise ChatStickerError("sticker_update_failed", "表情状态更新失败")
    scan_chat_sticker_media(settings)
    return _sticker_from_row(updated, public=False)  # type: ignore[return-value]


def get_sticker_image_file(
    activity_id: str,
    sticker_id: int,
    requested_image_id: str,
    settings: Settings,
) -> ChatStickerFile:
    with transaction(settings) as connection:
        row = _require_sticker(connection, activity_id, sticker_id)
    image_id = str(row["image_id"])
    if requested_image_id != image_id:
        raise ChatStickerError("image_not_found", "图片不存在")
    storage_key = str(row["image_storage_key"])
    try:
        path = storage_path(settings, storage_key, namespace=CHAT_STICKERS_NAMESPACE)
    except MediaError as error:
        logger.warning("表情图片存储标识无效")
        raise ChatStickerError("image_not_found", "图片不存在") from error
    if not path.is_file() or path.is_symlink():
        raise ChatStickerError("image_not_found", "图片不存在")
    return ChatStickerFile(image_id=image_id, mime=str(row["image_mime"]), path=path)


def scan_chat_sticker_media(settings: Settings, *, grace_seconds: int = 300) -> list[str]:
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT image_storage_key FROM activity_chat_stickers WHERE image_storage_key IS NOT NULL"
        ).fetchall()
    references = {str(row["image_storage_key"]) for row in rows}
    return scan_orphan_files(
        settings,
        references,
        namespace=CHAT_STICKERS_NAMESPACE,
        grace_seconds=grace_seconds,
    )
