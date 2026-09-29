from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from app.core.config import Settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_superuser INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activities (
    activity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT NOT NULL CHECK(status IN ('closed', 'open', 'ended')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lottery_configs (
    activity_id TEXT PRIMARY KEY REFERENCES activities(activity_id) ON DELETE CASCADE,
    no_repeat_across_prizes INTEGER NOT NULL DEFAULT 1 CHECK(no_repeat_across_prizes IN (0, 1)),
    rolling_name_count INTEGER NOT NULL DEFAULT 8 CHECK(rolling_name_count BETWEEN 1 AND 20),
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lottery_awards (
    award_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order >= 0),
    UNIQUE(activity_id, name)
);
CREATE TABLE IF NOT EXISTS lottery_prizes (
    prize_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    award_id INTEGER NOT NULL REFERENCES lottery_awards(award_id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 200),
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 100000),
    sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order >= 0),
    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK(is_enabled IN (0, 1)),
    image_id TEXT,
    image_storage_key TEXT,
    image_mime TEXT,
    image_size INTEGER,
    UNIQUE(activity_id, name)
);
CREATE TABLE IF NOT EXISTS activity_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    avatar_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    is_muted INTEGER NOT NULL DEFAULT 0 CHECK(is_muted IN (0, 1)),
    can_mobile_lottery INTEGER NOT NULL DEFAULT 0 CHECK(can_mobile_lottery IN (0, 1)),
    session_version INTEGER NOT NULL DEFAULT 0 CHECK(session_version >= 0),
    UNIQUE(activity_id, phone)
);
CREATE TABLE IF NOT EXISTS lottery_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    activity_user_id INTEGER NOT NULL REFERENCES activity_users(id) ON DELETE CASCADE,
    is_blacklisted INTEGER NOT NULL DEFAULT 0 CHECK(is_blacklisted IN (0, 1)),
    is_whitelisted INTEGER NOT NULL DEFAULT 0 CHECK(is_whitelisted IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(activity_id, activity_user_id)
);
CREATE INDEX IF NOT EXISTS idx_lottery_entries_activity
    ON lottery_entries(activity_id, activity_user_id);
CREATE INDEX IF NOT EXISTS idx_lottery_entries_activity_flags
    ON lottery_entries(activity_id, is_blacklisted, is_whitelisted, activity_user_id);
CREATE TABLE IF NOT EXISTS lottery_prize_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    prize_id INTEGER NOT NULL REFERENCES lottery_prizes(prize_id) ON DELETE CASCADE,
    activity_user_id INTEGER NOT NULL REFERENCES activity_users(id) ON DELETE CASCADE,
    is_blacklisted INTEGER NOT NULL DEFAULT 0 CHECK(is_blacklisted IN (0, 1)),
    is_whitelisted INTEGER NOT NULL DEFAULT 0 CHECK(is_whitelisted IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(activity_id, prize_id, activity_user_id),
    CHECK(NOT (is_blacklisted = 1 AND is_whitelisted = 1))
);
CREATE INDEX IF NOT EXISTS idx_lottery_prize_entries_activity_prize
    ON lottery_prize_entries(activity_id, prize_id, activity_user_id);
CREATE INDEX IF NOT EXISTS idx_lottery_prize_entries_flags
    ON lottery_prize_entries(activity_id, prize_id, is_blacklisted, is_whitelisted, activity_user_id);
CREATE TABLE IF NOT EXISTS lottery_prize_entry_migrations (
    activity_id TEXT PRIMARY KEY REFERENCES activities(activity_id) ON DELETE CASCADE,
    migrated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lottery_draws (
    draw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    award_id INTEGER NOT NULL REFERENCES lottery_awards(award_id) ON DELETE RESTRICT,
    prize_id INTEGER NOT NULL REFERENCES lottery_prizes(prize_id) ON DELETE RESTRICT,
    activity_user_id INTEGER NOT NULL REFERENCES activity_users(id) ON DELETE RESTRICT,
    draw_number INTEGER NOT NULL CHECK(draw_number >= 1),
    request_id TEXT NOT NULL,
    drawn_at TEXT NOT NULL,
    UNIQUE(activity_id, request_id),
    UNIQUE(activity_id, prize_id, draw_number)
);
CREATE INDEX IF NOT EXISTS idx_lottery_draws_activity
    ON lottery_draws(activity_id, draw_id);
CREATE INDEX IF NOT EXISTS idx_lottery_draws_prize
    ON lottery_draws(activity_id, prize_id, draw_id);
CREATE TABLE IF NOT EXISTS activity_chat_stickers (
    sticker_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    image_id TEXT NOT NULL UNIQUE,
    image_storage_key TEXT NOT NULL UNIQUE,
    image_mime TEXT NOT NULL,
    image_size INTEGER NOT NULL CHECK(image_size BETWEEN 1 AND 5242880),
    image_width INTEGER NOT NULL CHECK(image_width > 0),
    image_height INTEGER NOT NULL CHECK(image_height > 0),
    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK(is_enabled IN (0, 1)),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_chat_stickers_activity_status
    ON activity_chat_stickers(activity_id, is_enabled, sticker_id);
CREATE TABLE IF NOT EXISTS activity_chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    activity_user_id INTEGER NOT NULL REFERENCES activity_users(id) ON DELETE CASCADE,
    body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 500),
    created_at TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text' CHECK(message_type IN ('text', 'sticker')),
    sticker_id INTEGER REFERENCES activity_chat_stickers(sticker_id)
);
CREATE INDEX IF NOT EXISTS idx_activity_chat_messages_cursor
    ON activity_chat_messages(activity_id, message_id);
CREATE INDEX IF NOT EXISTS idx_activity_users_username
    ON activity_users(activity_id, username, id);
CREATE INDEX IF NOT EXISTS idx_activity_users_lottery_phone
    ON activity_users(activity_id, phone, username, id);
CREATE TABLE IF NOT EXISTS activity_danmaku_settings (
    activity_id TEXT PRIMARY KEY REFERENCES activities(activity_id) ON DELETE CASCADE,
    track_count INTEGER NOT NULL CHECK(track_count BETWEEN 1 AND 12),
    font_size INTEGER NOT NULL CHECK(font_size BETWEEN 16 AND 96),
    opacity REAL NOT NULL CHECK(opacity BETWEEN 0.1 AND 1.0),
    duration_seconds INTEGER NOT NULL CHECK(duration_seconds BETWEEN 5 AND 30),
    entry_interval_seconds REAL NOT NULL DEFAULT 1.0 CHECK(entry_interval_seconds BETWEEN 0.1 AND 5.0),
    max_wait_seconds REAL NOT NULL DEFAULT 1.5 CHECK(max_wait_seconds BETWEEN 0.5 AND 5.0),
    display_top INTEGER NOT NULL CHECK(display_top BETWEEN 0 AND 80),
    display_bottom INTEGER NOT NULL CHECK(display_bottom BETWEEN 20 AND 100),
    text_color TEXT NOT NULL,
    token_version INTEGER NOT NULL,
    token_created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK(display_bottom > display_top)
);
CREATE TABLE IF NOT EXISTS sms_verification_sends (
    phone TEXT PRIMARY KEY,
    last_sent_at INTEGER NOT NULL CHECK(last_sent_at >= 0)
);
"""


def connect(settings: Settings) -> sqlite3.Connection:
    path = Path(settings.database_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def transaction(settings: Settings) -> Iterator[sqlite3.Connection]:
    connection = connect(settings)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database(settings: Settings) -> None:
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        for statement in SCHEMA.split(";"):
            if statement.strip():
                connection.execute(statement)
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(activity_users)").fetchall()
        }
        if "avatar_id" not in columns:
            connection.execute("ALTER TABLE activity_users ADD COLUMN avatar_id INTEGER")
        if "is_active" not in columns:
            connection.execute(
                "ALTER TABLE activity_users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 "
                "CHECK(is_active IN (0, 1))"
            )
        if "is_muted" not in columns:
            connection.execute(
                "ALTER TABLE activity_users ADD COLUMN is_muted INTEGER NOT NULL DEFAULT 0 "
                "CHECK(is_muted IN (0, 1))"
            )
        if "can_mobile_lottery" not in columns:
            connection.execute(
                "ALTER TABLE activity_users ADD COLUMN can_mobile_lottery INTEGER NOT NULL DEFAULT 0 "
                "CHECK(can_mobile_lottery IN (0, 1))"
            )
        if "session_version" not in columns:
            connection.execute(
                "ALTER TABLE activity_users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0 "
                "CHECK(session_version >= 0)"
            )
        chat_message_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(activity_chat_messages)").fetchall()
        }
        if "message_type" not in chat_message_columns:
            connection.execute(
                "ALTER TABLE activity_chat_messages ADD COLUMN message_type TEXT NOT NULL DEFAULT 'text' "
                "CHECK(message_type IN ('text', 'sticker'))"
            )
        if "sticker_id" not in chat_message_columns:
            connection.execute(
                "ALTER TABLE activity_chat_messages ADD COLUMN sticker_id INTEGER "
                "REFERENCES activity_chat_stickers(sticker_id)"
            )
        danmaku_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(activity_danmaku_settings)").fetchall()
        }
        if "max_wait_seconds" not in danmaku_columns:
            connection.execute(
                "ALTER TABLE activity_danmaku_settings "
                "ADD COLUMN max_wait_seconds REAL NOT NULL DEFAULT 1.5 "
                "CHECK(max_wait_seconds BETWEEN 0.5 AND 5.0)"
            )
        if "entry_interval_seconds" not in danmaku_columns:
            connection.execute(
                "ALTER TABLE activity_danmaku_settings "
                "ADD COLUMN entry_interval_seconds REAL NOT NULL DEFAULT 1.0 "
                "CHECK(entry_interval_seconds BETWEEN 0.1 AND 5.0)"
            )
        lottery_prize_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(lottery_prizes)").fetchall()
        }
        optional_lottery_prize_columns = {
            "image_id": "TEXT",
            "image_storage_key": "TEXT",
            "image_mime": "TEXT",
            "image_size": "INTEGER",
        }
        for column, definition in optional_lottery_prize_columns.items():
            if column not in lottery_prize_columns:
                connection.execute(f"ALTER TABLE lottery_prizes ADD COLUMN {column} {definition}")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_lottery_prizes_image_id "
            "ON lottery_prizes(image_id) WHERE image_id IS NOT NULL"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_lottery_prizes_image_storage_key "
            "ON lottery_prizes(image_storage_key) WHERE image_storage_key IS NOT NULL"
        )
