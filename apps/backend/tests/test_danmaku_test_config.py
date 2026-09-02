import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.main import app
from app.modules.chat.service import ChatInvalidStickerError
from app.modules.danmaku import testing as danmaku_testing
from app.modules.danmaku.testing import (
    DanmakuTestConfig,
    DanmakuTestManager,
    TestUser as DanmakuTestUser,
    danmaku_test_manager,
)


def make_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "danmaku-test-config.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        danmaku_token_secret="separate-danmaku-test-secret",
        superuser_username="root",
        superuser_password="secret-password",
    )
    init_database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), settings


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_activity(client: TestClient, headers: dict[str, str], name: str) -> str:
    response = client.post("/api/v1/admin/activities", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["activity_id"]


def test_admin_danmaku_test_validates_config_and_creates_requested_users(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    activity_id = ""
    headers: dict[str, str] = {}
    original_main_settings = main_module.settings
    main_module.settings = settings
    client.__enter__()
    try:
        headers = admin_headers(client)
        activity_id = create_activity(client, headers, "弹幕测试配置校验")
        opened = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
        assert opened.status_code == 200

        config = {"user_count": 21, "min_delay_seconds": 0.2, "max_delay_seconds": 0.7}
        started = client.post(
            f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
            headers=headers,
            json=config,
        )
        assert started.status_code == 200
        assert {key: started.json()[key] for key in config} == config
        status_response = client.get(
            f"/api/v1/admin/activities/{activity_id}/danmaku/test",
            headers=headers,
        )
        assert status_response.status_code == 200
        assert {key: status_response.json()[key] for key in config} == config

        with transaction(settings) as connection:
            test_users = connection.execute(
                "SELECT username, avatar_id FROM activity_users WHERE activity_id = ? "
                "AND phone LIKE 'dmtest-%' ORDER BY id",
                (activity_id,),
            ).fetchall()
        assert len(test_users) == 21
        assert [row["username"] for row in test_users] == [f"弹幕测试用户{index}" for index in range(1, 22)]
        assert [row["avatar_id"] for row in test_users] == [*range(1, 21), 1]

        stopped = client.post(
            f"/api/v1/admin/activities/{activity_id}/danmaku/test/stop",
            headers=headers,
        )
        assert stopped.status_code == 200

        legacy_started = client.post(
            f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
            headers=headers,
        )
        assert legacy_started.status_code == 200
        assert {
            key: legacy_started.json()[key]
            for key in ("user_count", "min_delay_seconds", "max_delay_seconds")
        } == {
            "user_count": 6,
            "min_delay_seconds": 0.85,
            "max_delay_seconds": 0.85,
        }
        legacy_stopped = client.post(
            f"/api/v1/admin/activities/{activity_id}/danmaku/test/stop",
            headers=headers,
        )
        assert legacy_stopped.status_code == 200

        invalid_configs = (
            {"user_count": 0, "min_delay_seconds": 0, "max_delay_seconds": 1},
            {"user_count": 1, "min_delay_seconds": -0.1, "max_delay_seconds": 1},
            {"user_count": 1, "min_delay_seconds": 0, "max_delay_seconds": 60.1},
            {"user_count": 1, "min_delay_seconds": 2, "max_delay_seconds": 1},
        )
        for invalid_config in invalid_configs:
            response = client.post(
                f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
                headers=headers,
                json=invalid_config,
            )
            assert response.status_code == 422
    finally:
        if activity_id and danmaku_test_manager.is_running(activity_id):
            client.post(
                f"/api/v1/admin/activities/{activity_id}/danmaku/test/stop",
                headers=headers,
            )
        client.__exit__(None, None, None)
        main_module.settings = original_main_settings
        app.dependency_overrides.clear()


def test_danmaku_test_manager_runs_one_sender_per_user(monkeypatch) -> None:
    async def verify() -> None:
        manager = DanmakuTestManager()
        joined_at = datetime.now(timezone.utc)
        users = [
            DanmakuTestUser(activity_user_id=index, username=f"测试用户{index}", joined_at=joined_at)
            for index in range(1, 101)
        ]
        emitted: list[tuple[int, str]] = []
        message_id = 0

        def fake_create_message(_activity_id, principal, body, _settings):
            nonlocal message_id
            message_id += 1
            emitted.append((principal.activity_user_id, body))
            return SimpleNamespace(
                model_dump=lambda mode: {
                    "message_id": message_id,
                    "activity_id": "test-activity",
                    "body": body,
                    "created_at": "2026-08-28T00:00:00+00:00",
                }
            )

        async def fake_broadcast(*_args, **_kwargs) -> None:
            return None

        monkeypatch.setattr(danmaku_testing, "create_message", fake_create_message)
        monkeypatch.setattr(danmaku_testing.random, "random", lambda: 1.0)
        monkeypatch.setattr(danmaku_testing.chat_manager, "broadcast", fake_broadcast)
        monkeypatch.setattr(danmaku_testing.danmaku_manager, "broadcast_message", fake_broadcast)
        task = asyncio.create_task(
            manager._run(
                "test-activity",
                users,
                object(),
                DanmakuTestConfig(user_count=100, min_delay_seconds=0.01, max_delay_seconds=0.01),
            )
        )
        await asyncio.sleep(0.3)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert {user_id for user_id, _ in emitted} == set(range(1, 101))
        assert len(emitted) >= 100

    asyncio.run(verify())


def test_danmaku_test_selects_enabled_sticker_randomly(monkeypatch) -> None:
    sticker = SimpleNamespace(sticker_id=17)
    monkeypatch.setattr(danmaku_testing.random, "random", lambda: 0.0)
    monkeypatch.setattr(danmaku_testing.random, "choice", lambda options: options[0])
    monkeypatch.setattr(
        danmaku_testing,
        "list_stickers",
        lambda *_args, **_kwargs: [sticker],
    )

    body, sticker_id = danmaku_testing._select_test_payload("test-activity", object(), 0)

    assert body == danmaku_testing.TEST_MESSAGES[0]
    assert sticker_id == sticker.sticker_id


def test_danmaku_test_uses_text_without_enabled_stickers(monkeypatch) -> None:
    monkeypatch.setattr(danmaku_testing.random, "random", lambda: 0.0)
    monkeypatch.setattr(danmaku_testing, "list_stickers", lambda *_args, **_kwargs: [])

    body, sticker_id = danmaku_testing._select_test_payload("test-activity", object(), 1)

    assert body == danmaku_testing.TEST_MESSAGES[1]
    assert sticker_id is None


def test_danmaku_test_manager_broadcasts_selected_sticker(monkeypatch) -> None:
    async def verify() -> None:
        manager = DanmakuTestManager()
        user = DanmakuTestUser(
            activity_user_id=1,
            username="测试用户1",
            joined_at=datetime.now(timezone.utc),
        )
        sticker = SimpleNamespace(sticker_id=17)
        calls: list[tuple[str | None, int | None]] = []
        broadcasts: list[tuple[str, dict]] = []
        delivered = asyncio.Event()

        monkeypatch.setattr(danmaku_testing.random, "random", lambda: 0.0)
        monkeypatch.setattr(danmaku_testing, "list_stickers", lambda *_args, **_kwargs: [sticker])

        def fake_create_message(_activity_id, _principal, body, _settings, *, sticker_id=None):
            calls.append((body, sticker_id))
            return SimpleNamespace(
                model_dump=lambda mode: {
                    "message_id": 1,
                    "activity_id": "test-activity",
                    "body": "[表情] 开心",
                    "created_at": "2026-08-28T00:00:00+00:00",
                    "message_type": "sticker",
                    "sticker": {"sticker_id": sticker_id, "name": "开心"},
                }
            )

        async def fake_chat_broadcast(_activity_id, payload) -> None:
            broadcasts.append(("chat", payload))

        async def fake_danmaku_broadcast(_activity_id, payload) -> None:
            broadcasts.append(("danmaku", payload))
            delivered.set()

        monkeypatch.setattr(danmaku_testing, "create_message", fake_create_message)
        monkeypatch.setattr(danmaku_testing.chat_manager, "broadcast", fake_chat_broadcast)
        monkeypatch.setattr(danmaku_testing.danmaku_manager, "broadcast_message", fake_danmaku_broadcast)
        task = asyncio.create_task(
            manager._run_user(
                "test-activity",
                user,
                0,
                1,
                0.0,
                object(),
                DanmakuTestConfig(user_count=1, min_delay_seconds=60, max_delay_seconds=60),
                asyncio.Lock(),
            )
        )
        await asyncio.wait_for(delivered.wait(), timeout=1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        assert calls == [(None, 17)]
        assert [kind for kind, _payload in broadcasts] == ["chat", "danmaku"]
        assert broadcasts[0][1]["message"]["message_type"] == "sticker"
        assert broadcasts[1][1]["message_type"] == "sticker"
        assert broadcasts[1][1]["sticker"]["sticker_id"] == 17

    asyncio.run(verify())


def test_danmaku_test_falls_back_to_text_if_sticker_is_disabled(monkeypatch) -> None:
    sticker = SimpleNamespace(sticker_id=17)
    calls: list[tuple[str | None, int | None]] = []
    monkeypatch.setattr(danmaku_testing.random, "random", lambda: 0.0)
    monkeypatch.setattr(danmaku_testing, "list_stickers", lambda *_args, **_kwargs: [sticker])

    def fake_create_message(_activity_id, _principal, body, _settings, *, sticker_id=None):
        calls.append((body, sticker_id))
        if sticker_id is not None:
            raise ChatInvalidStickerError
        return SimpleNamespace()

    monkeypatch.setattr(danmaku_testing, "create_message", fake_create_message)

    danmaku_testing._create_test_message("test-activity", object(), 0, object())

    assert calls == [(None, 17), (danmaku_testing.TEST_MESSAGES[0], None)]
