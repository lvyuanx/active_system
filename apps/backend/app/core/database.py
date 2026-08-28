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
CREATE TABLE IF NOT EXISTS activity_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    avatar_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    is_muted INTEGER NOT NULL DEFAULT 0 CHECK(is_muted IN (0, 1)),
    session_version INTEGER NOT NULL DEFAULT 0 CHECK(session_version >= 0),
    UNIQUE(activity_id, phone)
);
CREATE TABLE IF NOT EXISTS activity_chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    activity_user_id INTEGER NOT NULL REFERENCES activity_users(id) ON DELETE CASCADE,
    body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 500),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_chat_messages_cursor
    ON activity_chat_messages(activity_id, message_id);
CREATE INDEX IF NOT EXISTS idx_activity_users_username
    ON activity_users(activity_id, username, id);
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
"""


def connect(settings: Settings) -> sqlite3.Connection:
    path = Path(settings.database_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path)
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
        if "session_version" not in columns:
            connection.execute(
                "ALTER TABLE activity_users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0 "
                "CHECK(session_version >= 0)"
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
