from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import re
import sqlite3

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import Settings
from app.core.database import transaction


DEFAULT_DANMAKU_SETTINGS = {
    "track_count": 6,
    "font_size": 36,
    "opacity": 0.9,
    "duration_seconds": 12,
    "entry_interval_seconds": 1.0,
    "max_wait_seconds": 1.5,
    "display_top": 10,
    "display_bottom": 90,
    "text_color": "#FFFFFF",
}
TOKEN_PREFIX = "dm1"
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class DanmakuSettingsInput(BaseModel):
    track_count: int = Field(ge=1, le=12)
    font_size: int = Field(ge=16, le=96)
    opacity: float = Field(ge=0.1, le=1.0)
    duration_seconds: int = Field(ge=5, le=30)
    entry_interval_seconds: float = Field(default=1.0, ge=0.1, le=5.0)
    max_wait_seconds: float = Field(default=1.5, ge=0.5, le=5.0)
    display_top: int = Field(ge=0, le=80)
    display_bottom: int = Field(ge=20, le=100)
    text_color: str

    @field_validator("text_color")
    @classmethod
    def validate_text_color(cls, value: str) -> str:
        color = value.strip().upper()
        if not COLOR_PATTERN.fullmatch(color):
            raise ValueError("文字颜色必须是六位十六进制颜色")
        return color

    @model_validator(mode="after")
    def validate_display_area(self) -> "DanmakuSettingsInput":
        if self.display_bottom <= self.display_top:
            raise ValueError("显示区域底部必须大于顶部")
        return self


class DanmakuSettings(DanmakuSettingsInput):
    pass


class DanmakuSettingsUpdate(DanmakuSettingsInput):
    pass


class DanmakuAdminResponse(BaseModel):
    activity_id: str
    settings: DanmakuSettings
    token: str
    token_created_at: datetime
    updated_at: datetime


class DanmakuSessionResponse(BaseModel):
    activity_id: str
    activity_name: str
    activity_status: str
    settings: DanmakuSettings
    latest_message_id: int


class DanmakuMessage(BaseModel):
    message_id: int
    activity_id: str
    body: str
    created_at: datetime


class DanmakuMessagePage(BaseModel):
    items: list[DanmakuMessage]
    has_more: bool


@dataclass(frozen=True)
class DanmakuRecord:
    activity_id: str
    settings: DanmakuSettings
    token_version: int
    token_created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DanmakuPrincipal:
    activity_id: str
    token_version: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _activity_or_raise(connection: sqlite3.Connection, activity_id: str) -> sqlite3.Row:
    activity = connection.execute(
        "SELECT activity_id, name, status FROM activities WHERE activity_id = ?",
        (activity_id,),
    ).fetchone()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
    return activity


def _ensure_record(connection: sqlite3.Connection, activity_id: str) -> sqlite3.Row:
    _activity_or_raise(connection, activity_id)
    now = _now()
    connection.execute(
        """INSERT OR IGNORE INTO activity_danmaku_settings(
            activity_id, track_count, font_size, opacity, duration_seconds, entry_interval_seconds,
            max_wait_seconds,
            display_top, display_bottom,
            text_color, token_version, token_created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            activity_id,
            DEFAULT_DANMAKU_SETTINGS["track_count"],
            DEFAULT_DANMAKU_SETTINGS["font_size"],
            DEFAULT_DANMAKU_SETTINGS["opacity"],
            DEFAULT_DANMAKU_SETTINGS["duration_seconds"],
            DEFAULT_DANMAKU_SETTINGS["entry_interval_seconds"],
            DEFAULT_DANMAKU_SETTINGS["max_wait_seconds"],
            DEFAULT_DANMAKU_SETTINGS["display_top"],
            DEFAULT_DANMAKU_SETTINGS["display_bottom"],
            DEFAULT_DANMAKU_SETTINGS["text_color"],
            now,
            now,
        ),
    )
    row = connection.execute(
        "SELECT * FROM activity_danmaku_settings WHERE activity_id = ?",
        (activity_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="弹幕配置初始化失败")
    return row


def _record_from_row(row: sqlite3.Row) -> DanmakuRecord:
    return DanmakuRecord(
        activity_id=str(row["activity_id"]),
        settings=DanmakuSettings(
            track_count=int(row["track_count"]),
            font_size=int(row["font_size"]),
            opacity=float(row["opacity"]),
            duration_seconds=int(row["duration_seconds"]),
            entry_interval_seconds=float(row["entry_interval_seconds"]),
            max_wait_seconds=float(row["max_wait_seconds"]),
            display_top=int(row["display_top"]),
            display_bottom=int(row["display_bottom"]),
            text_color=str(row["text_color"]),
        ),
        token_version=int(row["token_version"]),
        token_created_at=datetime.fromisoformat(str(row["token_created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
    )


def get_danmaku_record(activity_id: str, settings: Settings) -> DanmakuRecord:
    with transaction(settings) as connection:
        row = _ensure_record(connection, activity_id)
    return _record_from_row(row)


def update_danmaku_settings(
    activity_id: str,
    payload: DanmakuSettingsUpdate,
    settings: Settings,
) -> DanmakuRecord:
    now = _now()
    with transaction(settings) as connection:
        _ensure_record(connection, activity_id)
        connection.execute(
            """UPDATE activity_danmaku_settings SET
                track_count = ?, font_size = ?, opacity = ?, duration_seconds = ?, entry_interval_seconds = ?,
                max_wait_seconds = ?,
                display_top = ?,
                display_bottom = ?, text_color = ?, updated_at = ?
            WHERE activity_id = ?""",
            (
                payload.track_count,
                payload.font_size,
                payload.opacity,
                payload.duration_seconds,
                payload.entry_interval_seconds,
                payload.max_wait_seconds,
                payload.display_top,
                payload.display_bottom,
                payload.text_color,
                now,
                activity_id,
            ),
        )
        row = connection.execute(
            "SELECT * FROM activity_danmaku_settings WHERE activity_id = ?",
            (activity_id,),
        ).fetchone()
    return _record_from_row(row)


def regenerate_danmaku_token(activity_id: str, settings: Settings) -> DanmakuRecord:
    now = _now()
    with transaction(settings) as connection:
        current = _ensure_record(connection, activity_id)
        connection.execute(
            """UPDATE activity_danmaku_settings
            SET token_version = ?, token_created_at = ?, updated_at = ? WHERE activity_id = ?""",
            (int(current["token_version"]) + 1, now, now, activity_id),
        )
        row = connection.execute(
            "SELECT * FROM activity_danmaku_settings WHERE activity_id = ?",
            (activity_id,),
        ).fetchone()
    return _record_from_row(row)


def make_danmaku_token(activity_id: str, token_version: int, settings: Settings) -> str:
    secret = settings.danmaku_token_secret.strip() or settings.jwt_secret
    signed = f"danmaku:{activity_id}:{token_version}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"{TOKEN_PREFIX}.{activity_id}.{token_version}.{signature}"


def _invalid_token() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="弹幕 token 无效或已失效")


def authenticate_danmaku_token(token: str, settings: Settings) -> DanmakuPrincipal:
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != TOKEN_PREFIX:
        raise _invalid_token()
    _, activity_id, version_value, signature = parts
    try:
        token_version = int(version_value)
    except ValueError as error:
        raise _invalid_token() from error
    if token_version < 1:
        raise _invalid_token()
    try:
        record = get_danmaku_record(activity_id, settings)
    except HTTPException as error:
        if error.status_code == status.HTTP_404_NOT_FOUND:
            raise _invalid_token() from error
        raise
    expected = make_danmaku_token(activity_id, token_version, settings).rsplit(".", 1)[-1]
    if record.token_version != token_version or not hmac.compare_digest(signature, expected):
        raise _invalid_token()
    return DanmakuPrincipal(activity_id=activity_id, token_version=token_version)


def make_admin_response(record: DanmakuRecord, settings: Settings) -> DanmakuAdminResponse:
    return DanmakuAdminResponse(
        activity_id=record.activity_id,
        settings=record.settings,
        token=make_danmaku_token(record.activity_id, record.token_version, settings),
        token_created_at=record.token_created_at,
        updated_at=record.updated_at,
    )


def get_danmaku_session(principal: DanmakuPrincipal, settings: Settings) -> DanmakuSessionResponse:
    with transaction(settings) as connection:
        activity = _activity_or_raise(connection, principal.activity_id)
        record = _record_from_row(_ensure_record(connection, principal.activity_id))
        latest = connection.execute(
            "SELECT COALESCE(MAX(message_id), 0) AS latest_message_id "
            "FROM activity_chat_messages WHERE activity_id = ?",
            (principal.activity_id,),
        ).fetchone()
    return DanmakuSessionResponse(
        activity_id=principal.activity_id,
        activity_name=str(activity["name"]),
        activity_status=str(activity["status"]),
        settings=record.settings,
        latest_message_id=int(latest["latest_message_id"]),
    )


def list_danmaku_messages(
    principal: DanmakuPrincipal,
    settings: Settings,
    *,
    after_id: int = 0,
    limit: int = 100,
) -> DanmakuMessagePage:
    with transaction(settings) as connection:
        rows = connection.execute(
            """SELECT message_id, activity_id, body, created_at FROM activity_chat_messages
            WHERE activity_id = ? AND message_id > ? ORDER BY message_id ASC LIMIT ?""",
            (principal.activity_id, after_id, limit + 1),
        ).fetchall()
    has_more = len(rows) > limit
    return DanmakuMessagePage(
        items=[
            DanmakuMessage(
                message_id=int(row["message_id"]),
                activity_id=str(row["activity_id"]),
                body=str(row["body"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
            for row in rows[:limit]
        ],
        has_more=has_more,
    )
