from io import BytesIO
from pathlib import Path
import os
import sqlite3
import time
from unittest.mock import patch

from PIL import Image
import pytest

from app.core.config import Settings
from app.core.database import init_database
from app.modules.files.service import scan_orphan_files
from app.modules.files.service import MediaError
from app.modules.files import service as media_service
from app.modules.lottery.media_service import scan_lottery_media

from .test_lottery import create_activity, make_client, open_activity, register_user
from app.modules.lottery.service import draw_lottery


def image_bytes(image_format: str = "PNG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (12, 12), (210, 160, 60)).save(output, format=image_format)
    return output.getvalue()


def lottery_image_url(client, activity_id: str, headers: dict[str, str]) -> str:
    response = client.get(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["prizes"][0]["image_url"]


def test_lottery_image_upload_replace_delete_and_public_read(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "奖品图片")
        prize_id = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers
        ).json()["prizes"][0]["prize_id"]
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            assert screen.receive_json()["type"] == "lottery.ready"
            upload = client.post(
                f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
                headers=headers,
                files={"file": ("prize.png", image_bytes(), "image/png")},
            )
            assert upload.status_code == 201, upload.text
            image = upload.json()
            assert image["mime"] == "image/png"
            assert image["size"] > 0
            first_url = image["image_url"]
            first_path = Path(settings.media_root) / "lottery-prizes" / f"{image['image_id']}.png"
            assert first_path.is_file()
            assert client.get(first_url.split("?", 1)[0]).status_code == 422
            assert client.get(first_url).status_code == 200
            config_event = screen.receive_json()
            assert config_event["type"] == "lottery.config.updated"
            assert config_event["config"]["prizes"][0]["image_url"] == first_url

        replacement = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
            files={"file": ("replacement.webp", image_bytes("WEBP"), "image/webp")},
        )
        assert replacement.status_code == 201, replacement.text
        second = replacement.json()
        assert second["image_id"] != image["image_id"]
        assert client.get(first_url).status_code == 404
        assert not first_path.exists()
        assert lottery_image_url(client, activity_id, headers) == second["image_url"]

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            assert screen.receive_json()["type"] == "lottery.ready"
            deleted = client.delete(
                f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
                headers=headers,
            )
            assert deleted.status_code == 200
            assert deleted.json() == {"image_url": None, "image_id": None, "mime": None, "size": None}
            assert screen.receive_json()["config"]["prizes"][0]["image_url"] is None
        assert client.get(second["image_url"]).status_code == 404
        assert lottery_image_url(client, activity_id, headers) is None
    finally:
        client.close()


def test_lottery_image_rejects_invalid_content_size_and_activity_user(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "图片安全")
        config = client.get(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers).json()
        prize_id = config["prizes"][0]["prize_id"]
        invalid = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
            files={"file": ("fake.png", b"<svg></svg>", "image/png")},
        )
        assert invalid.status_code == 422
        too_large = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
            files={"file": ("large.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
        )
        assert too_large.status_code == 413
        assert lottery_image_url(client, activity_id, headers) is None
        user = register_user(client, activity_id, "参与者", "13800004001")
        forbidden = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers={"Authorization": f"Bearer {user['access_token']}"},
            files={"file": ("x.png", image_bytes(), "image/png")},
        )
        assert forbidden.status_code == 401
    finally:
        client.close()


def test_lottery_image_migration_and_orphan_cleanup(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE activities (activity_id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE lottery_awards (award_id INTEGER PRIMARY KEY, activity_id TEXT NOT NULL,
          name TEXT NOT NULL, sort_order INTEGER NOT NULL);
        CREATE TABLE lottery_prizes (prize_id INTEGER PRIMARY KEY, activity_id TEXT NOT NULL,
          award_id INTEGER NOT NULL, name TEXT NOT NULL, quantity INTEGER NOT NULL,
          sort_order INTEGER NOT NULL, is_enabled INTEGER NOT NULL);
        """
    )
    connection.commit()
    connection.close()
    settings = Settings(database_path=str(database_path), media_root=str(tmp_path / "media"))
    init_database(settings)
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(lottery_prizes)")}
    assert {"image_id", "image_storage_key", "image_mime", "image_size"} <= columns

    orphan = Path(settings.media_root) / "lottery-prizes" / "orphan.png"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(image_bytes())
    old_time = time.time() - 3600
    os.utime(orphan, (old_time, old_time))
    assert len(scan_orphan_files(settings, set(), grace_seconds=0)) == 1
    assert not orphan.exists()


def test_decompression_bomb_is_rejected_as_image_error(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "bomb.png"
    path.write_bytes(image_bytes())

    def raise_bomb(_path):
        raise Image.DecompressionBombError("dimensions are unsafe")

    monkeypatch.setattr(Image, "open", raise_bomb)
    with pytest.raises(MediaError) as error:
        media_service._validate_image_file(path, ".png", "image/png")
    assert error.value.code == "invalid_image"


def test_lottery_image_accepts_all_formats_boundary_and_rejects_mime_mismatch(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "图片格式")
        prize_id = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers
        ).json()["prizes"][0]["prize_id"]
        for filename, image_format, mime in (
            ("prize.jpg", "JPEG", "image/jpeg"),
            ("prize.png", "PNG", "image/png"),
            ("prize.webp", "WEBP", "image/webp"),
        ):
            response = client.post(
                f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
                headers=headers,
                files={"file": (filename, image_bytes(image_format), mime)},
            )
            assert response.status_code == 201, response.text
        boundary = image_bytes("PNG")
        boundary += b"\x00" * (5 * 1024 * 1024 - len(boundary))
        response = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
            files={"file": ("boundary.png", boundary, "image/png")},
        )
        assert response.status_code == 201, response.text
        assert response.json()["size"] == 5 * 1024 * 1024
        mismatches = (
            ("wrong.jpg", image_bytes("PNG"), "image/png"),
            ("wrong.png", image_bytes("PNG"), "image/jpeg"),
            ("wrong.png", image_bytes("WEBP"), "image/png"),
        )
        for filename, content, mime in mismatches:
            response = client.post(
                f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
                headers=headers,
                files={"file": (filename, content, mime)},
            )
            assert response.status_code == 422, response.text
    finally:
        client.close()


def test_lottery_image_failure_keeps_original_and_public_headers_are_safe(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "失败保留")
        prize_id = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers
        ).json()["prizes"][0]["prize_id"]
        upload = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
            files={"file": ("original.png", image_bytes(), "image/png")},
        )
        assert upload.status_code == 201, upload.text
        original = upload.json()
        failed = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
            files={"file": ("broken.png", b"<script>alert(1)</script>", "image/png")},
        )
        assert failed.status_code == 422
        public = client.get(original["image_url"])
        assert public.status_code == 200
        assert public.headers["content-type"].startswith("image/png")
        assert public.headers["cache-control"].startswith("public, max-age=")
        assert public.headers["x-content-type-options"] == "nosniff"
        admin = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
        )
        assert admin.status_code == 200
        assert admin.headers["cache-control"] == "no-store"
        assert admin.headers["x-content-type-options"] == "nosniff"
        config = client.get(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers).json()
        assert config["prizes"][0]["image_url"] == original["image_url"]
        payload = {
            "no_repeat_across_prizes": config["no_repeat_across_prizes"],
            "rolling_name_count": config["rolling_name_count"],
            "awards": config["awards"],
            "prizes": [
                {key: prize[key] for key in ("prize_id", "award_id", "name", "quantity", "sort_order", "is_enabled")}
                for prize in config["prizes"]
            ],
        }
        saved = client.put(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers, json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()["prizes"][0]["image_url"] == original["image_url"]
        assert Path(settings.media_root, "lottery-prizes").exists()
    finally:
        client.close()


def test_lottery_image_cross_activity_permissions_and_cleanup_retry(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_a, headers = create_activity(client, "活动 A")
        activity_b, _ = create_activity(client, "活动 B")
        config_a = client.get(f"/api/v1/admin/activities/{activity_a}/lottery", headers=headers).json()
        config_b = client.get(f"/api/v1/admin/activities/{activity_b}/lottery", headers=headers).json()
        prize_a = config_a["prizes"][0]["prize_id"]
        prize_b = config_b["prizes"][0]["prize_id"]
        media_dir = Path(settings.media_root) / "lottery-prizes"
        files_before = set(media_dir.glob("*"))
        upload = client.post(
            f"/api/v1/admin/activities/{activity_a}/lottery/prizes/{prize_a}/image",
            headers=headers,
            files={"file": ("isolated.png", image_bytes(), "image/png")},
        )
        assert upload.status_code == 201
        image_url = upload.json()["image_url"]
        assert image_url.startswith(f"/api/v1/activities/{activity_a}/")
        stored_files = set(media_dir.glob("*")) - files_before
        assert len(stored_files) == 1
        assert client.get(f"/api/v1/activities/{activity_b}/lottery/prizes/{prize_b}/image?v=bad").status_code == 404
        assert client.post(
            f"/api/v1/admin/activities/{activity_a}/lottery/prizes/{prize_b}/image",
            headers=headers,
            files={"file": ("wrong-prize.png", image_bytes(), "image/png")},
        ).status_code == 404
        user = register_user(client, activity_a, "普通用户", "13800004002")
        user_headers = {"Authorization": f"Bearer {user['access_token']}"}
        assert client.get(
            f"/api/v1/admin/activities/{activity_a}/lottery/prizes/{prize_a}/image", headers=user_headers
        ).status_code == 401
        old_path = next(iter(stored_files))
        with patch("app.modules.lottery.media_service.remove_storage_key", return_value=False):
            deleted = client.delete(
                f"/api/v1/admin/activities/{activity_a}/lottery/prizes/{prize_a}/image", headers=headers
            )
        assert deleted.status_code == 200
        assert old_path.exists()
        assert scan_lottery_media(settings, grace_seconds=0)
        assert not old_path.exists()
    finally:
        client.close()


def test_lottery_config_prize_delete_removes_bound_media(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "配置删除图片")
        config = client.get(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers).json()
        prize = config["prizes"][0]
        uploaded = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize['prize_id']}/image",
            headers=headers,
            files={"file": ("remove-on-delete.png", image_bytes(), "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        storage_path = Path(settings.media_root) / "lottery-prizes" / f"{uploaded.json()['image_id']}.png"
        assert storage_path.is_file()
        payload = {
            "no_repeat_across_prizes": config["no_repeat_across_prizes"],
            "rolling_name_count": config["rolling_name_count"],
            "awards": config["awards"],
            "prizes": [],
        }
        deleted = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers, json=payload
        )
        assert deleted.status_code == 200, deleted.text
        assert not storage_path.exists()
    finally:
        client.close()


def test_lottery_config_award_cascade_removes_bound_media(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "级联删除图片")
        config = client.get(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers).json()
        prize_id = config["prizes"][0]["prize_id"]
        uploaded = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize_id}/image",
            headers=headers,
            files={"file": ("cascade-delete.png", image_bytes(), "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        storage_path = Path(settings.media_root) / "lottery-prizes" / f"{uploaded.json()['image_id']}.png"
        assert storage_path.is_file()
        deleted = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery",
            headers=headers,
            json={
                "no_repeat_across_prizes": config["no_repeat_across_prizes"],
                "rolling_name_count": config["rolling_name_count"],
                "awards": [],
                "prizes": [],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert not storage_path.exists()
    finally:
        client.close()


def test_lottery_config_prize_delete_with_draw_keeps_media(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "中奖图片保留")
        config = client.get(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers).json()
        prize = config["prizes"][0]
        uploaded = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/prizes/{prize['prize_id']}/image",
            headers=headers,
            files={"file": ("keep-on-failure.png", image_bytes(), "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        storage_path = Path(settings.media_root) / "lottery-prizes" / f"{uploaded.json()['image_id']}.png"
        user = register_user(client, activity_id, "中奖用户", "13800004003")
        open_activity(client, activity_id, headers)
        draw_lottery(activity_id, int(prize["prize_id"]), "delete-blocked", settings)
        payload = {
            "no_repeat_across_prizes": config["no_repeat_across_prizes"],
            "rolling_name_count": config["rolling_name_count"],
            "awards": config["awards"],
            "prizes": [],
        }
        blocked = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers, json=payload
        )
        assert blocked.status_code == 409, blocked.text
        assert storage_path.is_file()
        assert user["activity_user_id"]
    finally:
        client.close()
