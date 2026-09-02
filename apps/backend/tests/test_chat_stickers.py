from io import BytesIO
import os
from pathlib import Path
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.database import init_database
from app.core.security import create_access_token
from app.main import app

from .test_chat import admin_headers, create_activity, make_client, open_activity, register_user


def image_bytes(image_format: str = "PNG") -> bytes:
    output = BytesIO()
    first = Image.new("RGBA", (32, 20), (210, 160, 60, 255))
    if image_format == "GIF":
        second = Image.new("RGBA", (32, 20), (60, 160, 210, 255))
        first.save(
            output,
            format=image_format,
            save_all=True,
            append_images=[second],
            duration=40,
            loop=0,
        )
    elif image_format == "JPEG":
        first.convert("RGB").save(output, format=image_format)
    else:
        first.save(output, format=image_format)
    return output.getvalue()


def upload_sticker(
    client: TestClient,
    activity_id: str,
    headers: dict[str, str],
    filename: str,
    content: bytes,
    mime: str,
):
    response = client.post(
        f"/api/v1/admin/activities/{activity_id}/chat/stickers",
        headers=headers,
        files={"file": (filename, content, mime)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sticker_uploads_formats_lists_and_activity_isolation(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    settings.media_root = str(tmp_path / "media")
    try:
        activity_id, headers = create_activity(client, name="表情活动")
        other_activity_id, other_headers = create_activity(client, name="其它活动")
        png = upload_sticker(client, activity_id, headers, "开心.png", image_bytes(), "image/png")
        gif = upload_sticker(client, activity_id, headers, "动图.gif", image_bytes("GIF"), "image/gif")
        jpeg = upload_sticker(client, activity_id, headers, "照片.jpg", image_bytes("JPEG"), "image/jpeg")

        assert png["name"] == "开心"
        assert png["width"] == 32
        assert png["height"] == 20
        assert gif["mime"] == "image/gif"
        assert gif["name"] == "动图"
        assert jpeg["mime"] == "image/jpeg"
        assert client.get(png["image_url"]).status_code == 200
        assert client.get(gif["image_url"]).headers["content-type"] == "image/gif"
        assert client.get(f"{png['image_url'].split('?', 1)[0]}?v=stale").status_code == 404

        admin_list = client.get(
            f"/api/v1/admin/activities/{activity_id}/chat/stickers", headers=headers
        )
        assert admin_list.status_code == 200
        assert [item["name"] for item in admin_list.json()] == ["开心", "动图", "照片"]

        user_token = register_user(client, activity_id, "表情用户", "13800005001")
        user_list = client.get(
            f"/api/v1/activities/{activity_id}/chat/stickers",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert user_list.status_code == 200
        assert [item["sticker_id"] for item in user_list.json()] == [
            png["sticker_id"], gif["sticker_id"], jpeg["sticker_id"]
        ]

        other_list = client.get(
            f"/api/v1/activities/{other_activity_id}/chat/stickers", headers=other_headers
        )
        assert other_list.status_code == 403
        assert client.get(
            f"/api/v1/activities/{other_activity_id}/chat/stickers",
            headers={"Authorization": f"Bearer {user_token}"},
        ).status_code == 403
        assert client.get(
            f"/api/v1/activities/{other_activity_id}/chat/stickers/{png['sticker_id']}/image?v={png['image_id']}"
        ).status_code == 404
        assert client.get(
            f"/api/v1/admin/activities/{activity_id}/chat/stickers", headers={}
        ).status_code == 401
        assert client.post(
            f"/api/v1/admin/activities/{activity_id}/chat/stickers",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("blocked.png", image_bytes(), "image/png")},
        ).status_code == 401

        sticker_path = Path(settings.media_root) / "chat-stickers" / f"{png['image_id']}.png"
        assert sticker_path.is_file()
    finally:
        app.dependency_overrides.clear()


def test_sticker_upload_rejects_invalid_content_and_size(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    settings.media_root = str(tmp_path / "media")
    try:
        activity_id, headers = create_activity(client, name="表情校验")
        endpoint = f"/api/v1/admin/activities/{activity_id}/chat/stickers"
        invalid = client.post(
            endpoint,
            headers=headers,
            files={"file": ("fake.png", b"<svg></svg>", "image/png")},
        )
        assert invalid.status_code == 422
        mismatch = client.post(
            endpoint,
            headers=headers,
            files={"file": ("wrong.png", image_bytes("GIF"), "image/png")},
        )
        assert mismatch.status_code == 422
        unsupported = client.post(
            endpoint,
            headers=headers,
            files={"file": ("video.mp4", b"video", "video/mp4")},
        )
        assert unsupported.status_code == 422
        too_large = client.post(
            endpoint,
            headers=headers,
            files={"file": ("large.gif", b"x" * (5 * 1024 * 1024 + 1), "image/gif")},
        )
        assert too_large.status_code == 413
        assert client.get(endpoint, headers=headers).json() == []
    finally:
        app.dependency_overrides.clear()


def test_sticker_websocket_history_danmaku_and_soft_disable(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    settings.media_root = str(tmp_path / "media")
    try:
        activity_id, headers = create_activity(client, name="表情实时")
        sticker = upload_sticker(client, activity_id, headers, "鼓掌.webp", image_bytes("WEBP"), "image/webp")
        user_token = register_user(client, activity_id, "表情发送者", "13800005002")
        open_activity(client, activity_id, headers)
        user_id = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {user_token}"},
        ).json()["activity_user_id"]
        danmaku_token = client.get(
            f"/api/v1/admin/activities/{activity_id}/danmaku", headers=headers
        ).json()["token"]

        muted = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/{user_id}/mute",
            headers=headers,
        )
        assert muted.status_code == 200
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as muted_ws:
            muted_ws.send_json({"type": "auth", "token": user_token})
            assert muted_ws.receive_json()["type"] == "chat.ready"
            muted_ws.send_json({"type": "message.send", "sticker_id": sticker["sticker_id"]})
            assert muted_ws.receive_json()["code"] == "muted"
        unmuted = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/{user_id}/unmute",
            headers=headers,
        )
        assert unmuted.status_code == 200

        with client.websocket_connect("/api/v1/danmaku/ws") as danmaku_ws:
            danmaku_ws.send_json({"type": "auth", "token": danmaku_token})
            assert danmaku_ws.receive_json()["type"] == "danmaku.ready"
            with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as chat_ws:
                chat_ws.send_json({"type": "auth", "token": user_token})
                assert chat_ws.receive_json()["type"] == "chat.ready"
                chat_ws.send_json({"type": "message.send", "sticker_id": sticker["sticker_id"]})
                chat_event = chat_ws.receive_json()
                danmaku_event = danmaku_ws.receive_json()

                assert chat_event["type"] == "message.created"
                message = chat_event["message"]
                assert message["message_type"] == "sticker"
                assert message["body"] == "[表情] 鼓掌"
                assert message["sticker"]["image_url"] == sticker["image_url"]
                assert danmaku_event["type"] == "danmaku.message.created"
                assert "sender_username" not in danmaku_event["message"]
                assert danmaku_event["message"]["sticker"]["sticker_id"] == sticker["sticker_id"]
                message_id = message["message_id"]

                chat_ws.send_json({"type": "message.send", "body": "不应混合", "sticker_id": sticker["sticker_id"]})
                assert chat_ws.receive_json()["code"] == "invalid_sticker"

                disabled = client.delete(
                    f"/api/v1/admin/activities/{activity_id}/chat/stickers/{sticker['sticker_id']}",
                    headers=headers,
                )
                assert disabled.status_code == 200
                assert disabled.json()["is_enabled"] is False
                assert client.get(
                    f"/api/v1/activities/{activity_id}/chat/stickers",
                    headers={"Authorization": f"Bearer {user_token}"},
                ).json() == []
                chat_ws.send_json({"type": "message.send", "sticker_id": sticker["sticker_id"]})
                assert chat_ws.receive_json()["code"] == "invalid_sticker"

        closed = client.post(f"/api/v1/admin/activities/{activity_id}/close", headers=headers)
        assert closed.status_code == 200
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as closed_ws:
            closed_ws.send_json({"type": "auth", "token": user_token})
            assert closed_ws.receive_json()["type"] == "chat.ready"
            closed_ws.send_json({"type": "message.send", "sticker_id": sticker["sticker_id"]})
            assert closed_ws.receive_json()["code"] == "read_only"
        open_activity(client, activity_id, headers)

        history = client.get(
            f"/api/v1/activities/{activity_id}/chat/messages",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert history.status_code == 200
        assert history.json()["items"][0]["message_type"] == "sticker"
        assert history.json()["items"][0]["sticker"]["name"] == "鼓掌"
        assert client.get(sticker["image_url"]).status_code == 200

        danmaku_history = client.get(
            f"/api/v1/danmaku/messages?after_id={message_id - 1}",
            headers={"Authorization": f"Bearer {danmaku_token}"},
        )
        assert danmaku_history.status_code == 200
        assert danmaku_history.json()["items"][0]["message_type"] == "sticker"
        assert danmaku_history.json()["items"][0]["sticker"]["sticker_id"] == sticker["sticker_id"]

        restored = client.post(
            f"/api/v1/admin/activities/{activity_id}/chat/stickers/{sticker['sticker_id']}/restore",
            headers=headers,
        )
        assert restored.status_code == 200
        assert restored.json()["is_enabled"] is True
    finally:
        app.dependency_overrides.clear()


def test_legacy_chat_database_migrates_without_losing_text(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy-chat.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE activities (
            activity_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT, start_time TEXT, end_time TEXT,
            status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE activity_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, activity_id TEXT NOT NULL, username TEXT NOT NULL,
            phone TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE activity_chat_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT, activity_id TEXT NOT NULL,
            activity_user_id INTEGER NOT NULL, body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 500),
            created_at TEXT NOT NULL
        );
        INSERT INTO activities VALUES ('legacy-activity', '旧活动', NULL, NULL, NULL, 'open',
          '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');
        INSERT INTO activity_users(activity_id, username, phone, created_at)
          VALUES ('legacy-activity', '旧用户', '13800005003', '2026-01-01T00:00:00+00:00');
        INSERT INTO activity_chat_messages(activity_id, activity_user_id, body, created_at)
          VALUES ('legacy-activity', 1, '旧文本', '2026-01-01T00:00:01+00:00');
        """
    )
    connection.commit()
    connection.close()
    settings = Settings(
        database_path=str(database_path),
        media_root=str(tmp_path / "media"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    init_database(settings)
    with sqlite3.connect(database_path) as migrated:
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(activity_chat_messages)")}
        sticker_table = migrated.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'activity_chat_stickers'"
        ).fetchone()
    assert {"message_type", "sticker_id"} <= columns
    assert sticker_table is not None

    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        token = create_access_token(
            "旧用户",
            settings,
            activity_id="legacy-activity",
            activity_user_id=1,
            activity_user_session_version=0,
        )
        history = client.get(
            "/api/v1/activities/legacy-activity/chat/messages",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert history.status_code == 200
        assert history.json()["items"] == [
            {
                "message_id": 1,
                "activity_id": "legacy-activity",
                "sender_activity_user_id": 1,
                "sender_username": "旧用户",
                "body": "旧文本",
                "created_at": "2026-01-01T00:00:01Z",
                "message_type": "text",
                "sticker": None,
            }
        ]
        with client.websocket_connect("/api/v1/activities/legacy-activity/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "chat.ready"
            websocket.send_json({"type": "message.send", "body": "迁移后仍可发文本"})
            created = websocket.receive_json()["message"]
            assert created["message_type"] == "text"
            assert created["sticker"] is None
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_storage_path_rejects_namespace_symlink(tmp_path: Path) -> None:
    from app.modules.files.service import CHAT_STICKERS_NAMESPACE, MediaError, storage_path

    media_root = tmp_path / "media"
    media_root.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    namespace_root = media_root / CHAT_STICKERS_NAMESPACE
    try:
        namespace_root.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("当前 Windows 环境不允许创建目录符号链接")
    settings = Settings(
        database_path=str(tmp_path / "db.sqlite"),
        media_root=str(media_root),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    with pytest.raises(MediaError):
        storage_path(
            settings,
            f"{CHAT_STICKERS_NAMESPACE}/image.png",
            namespace=CHAT_STICKERS_NAMESPACE,
        )


def test_chat_sticker_orphan_scan_only_removes_unreferenced_files(tmp_path: Path) -> None:
    from app.modules.chat.stickers import scan_chat_sticker_media
    from app.modules.files.service import CHAT_STICKERS_NAMESPACE, chat_sticker_media_root

    settings = Settings(
        database_path=str(tmp_path / "db.sqlite"),
        media_root=str(tmp_path / "media"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    init_database(settings)
    namespace_root = chat_sticker_media_root(settings)
    orphan = namespace_root / "orphan.png"
    orphan.write_bytes(image_bytes())
    old_time = time.time() - 10
    orphan.touch()
    os.utime(orphan, (old_time, old_time))
    assert scan_chat_sticker_media(settings, grace_seconds=0) == [
        f"{CHAT_STICKERS_NAMESPACE}/orphan.png"
    ]
    assert not orphan.exists()


def test_media_temp_parent_and_scan_root_symlinks_never_escape_media_root(tmp_path: Path) -> None:
    from app.modules.chat.stickers import scan_chat_sticker_media
    from app.modules.files.service import (
        CHAT_STICKERS_NAMESPACE,
        MediaError,
        temporary_media_root,
    )

    media_root = tmp_path / "media"
    media_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    settings = Settings(
        database_path=str(tmp_path / "db.sqlite"),
        media_root=str(media_root),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    init_database(settings)
    temporary_root = media_root / ".tmp"
    try:
        temporary_root.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("当前 Windows 环境不允许创建目录符号链接")
    with pytest.raises(MediaError):
        temporary_media_root(settings, CHAT_STICKERS_NAMESPACE)
    temporary_root.unlink()

    namespace_root = media_root / CHAT_STICKERS_NAMESPACE
    namespace_root.symlink_to(outside, target_is_directory=True)
    sentinel = outside / "sentinel.png"
    sentinel.write_bytes(image_bytes())
    assert scan_chat_sticker_media(settings, grace_seconds=0) == []
    assert sentinel.is_file()
