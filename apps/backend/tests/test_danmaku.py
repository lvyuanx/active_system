import asyncio
from pathlib import Path
import time

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.main as main_module
from app.core.config import Settings, get_settings
from app.core.database import init_database
from app.main import app
from app.modules.danmaku.manager import DanmakuConnectionManager
from app.modules.danmaku.testing import TEST_USER_COUNT, danmaku_test_manager


def make_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "danmaku.db"),
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


def register_user(client: TestClient, activity_id: str) -> str:
    response = client.post(
        f"/api/v1/activities/{activity_id}/auth/register",
        json={"username": "弹幕用户", "phone": "13800000999"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def danmaku_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class DummyDanmakuWebSocket:
    def __init__(self) -> None:
        self.closed_code: int | None = None

    async def close(self, code: int, reason: str) -> None:
        self.closed_code = code


def test_danmaku_manager_rejects_old_token_connection_after_rotation() -> None:
    async def verify() -> None:
        manager = DanmakuConnectionManager()
        current = DummyDanmakuWebSocket()
        assert await manager.connect("rotation-activity", current, token_version=1) is True
        await manager.invalidate_activity("rotation-activity", token_version=2)
        assert current.closed_code == 4001
        stale = DummyDanmakuWebSocket()
        assert await manager.connect("rotation-activity", stale, token_version=1) is False
        fresh = DummyDanmakuWebSocket()
        assert await manager.connect("rotation-activity", fresh, token_version=2) is True

    asyncio.run(verify())


def test_danmaku_settings_are_validated_isolated_and_token_rotation_revokes_old_token(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        headers = admin_headers(client)
        first_id = create_activity(client, headers, "第一场弹幕活动")
        second_id = create_activity(client, headers, "第二场弹幕活动")

        first = client.get(f"/api/v1/admin/activities/{first_id}/danmaku", headers=headers)
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["settings"] == {
            "track_count": 6,
            "font_size": 36,
            "opacity": 0.9,
            "duration_seconds": 12,
            "display_top": 10,
            "display_bottom": 90,
            "text_color": "#FFFFFF",
        }
        stable_token = client.get(f"/api/v1/admin/activities/{first_id}/danmaku", headers=headers).json()["token"]
        assert stable_token == first_body["token"]

        updated = client.put(
            f"/api/v1/admin/activities/{first_id}/danmaku",
            headers=headers,
            json={
                "track_count": 9,
                "font_size": 48,
                "opacity": 0.65,
                "duration_seconds": 8,
                "display_top": 15,
                "display_bottom": 85,
                "text_color": "#12ab34",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["settings"]["text_color"] == "#12AB34"
        second = client.get(f"/api/v1/admin/activities/{second_id}/danmaku", headers=headers)
        assert second.json()["settings"]["track_count"] == 6

        invalid = client.put(
            f"/api/v1/admin/activities/{first_id}/danmaku",
            headers=headers,
            json={
                "track_count": 9,
                "font_size": 48,
                "opacity": 0.65,
                "duration_seconds": 8,
                "display_top": 85,
                "display_bottom": 85,
                "text_color": "blue",
            },
        )
        assert invalid.status_code == 422

        session = client.get("/api/v1/danmaku/session", headers=danmaku_headers(stable_token))
        assert session.status_code == 200
        assert session.json()["activity_id"] == first_id

        with client.websocket_connect("/api/v1/danmaku/ws") as active_websocket:
            active_websocket.send_json({"type": "auth", "token": stable_token})
            assert active_websocket.receive_json()["type"] == "danmaku.ready"
            rotated = client.post(f"/api/v1/admin/activities/{first_id}/danmaku/token", headers=headers)
            try:
                active_websocket.receive_json()
                disconnected = False
            except WebSocketDisconnect:
                disconnected = True
        assert disconnected is True
        assert rotated.status_code == 200
        fresh_token = rotated.json()["token"]
        assert fresh_token != stable_token
        assert client.get("/api/v1/danmaku/session", headers=danmaku_headers(stable_token)).status_code == 401
        assert client.get("/api/v1/danmaku/session", headers=danmaku_headers(fresh_token)).status_code == 200

        with client.websocket_connect("/api/v1/danmaku/ws") as websocket:
            websocket.send_json({"type": "auth", "token": stable_token})
            assert websocket.receive_json() == {
                "type": "danmaku.error",
                "code": "unauthorized",
                "detail": "弹幕 token 无效或已失效",
            }
            try:
                websocket.receive_json()
            except WebSocketDisconnect:
                pass
    finally:
        app.dependency_overrides.clear()


def test_danmaku_websocket_broadcasts_message_summary_and_live_settings(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        headers = admin_headers(client)
        activity_id = create_activity(client, headers, "实时弹幕活动")
        danmaku = client.get(f"/api/v1/admin/activities/{activity_id}/danmaku", headers=headers).json()
        token = danmaku["token"]
        user_token = register_user(client, activity_id)

        with client.websocket_connect("/api/v1/danmaku/ws") as danmaku_ws:
            danmaku_ws.send_json({"type": "auth", "token": token})
            ready = danmaku_ws.receive_json()
            assert ready["type"] == "danmaku.ready"
            assert ready["session"]["latest_message_id"] == 0

            opened = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
            assert opened.status_code == 200
            with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as chat_ws:
                chat_ws.send_json({"type": "auth", "token": user_token})
                assert chat_ws.receive_json()["type"] == "chat.ready"
                chat_ws.send_json({"type": "message.send", "body": "  只显示正文  "})
                chat_event = chat_ws.receive_json()
                danmaku_event = danmaku_ws.receive_json()
                assert chat_event["type"] == "message.created"
                assert chat_event["message"]["sender_username"] == "弹幕用户"
                assert danmaku_event["type"] == "danmaku.message.created"
                assert set(danmaku_event["message"]) == {"message_id", "activity_id", "body", "created_at"}
                assert danmaku_event["message"]["body"] == "只显示正文"
                message_id = danmaku_event["message"]["message_id"]

                updated = client.put(
                    f"/api/v1/admin/activities/{activity_id}/danmaku",
                    headers=headers,
                    json={
                        "track_count": 4,
                        "font_size": 52,
                        "opacity": 0.7,
                        "duration_seconds": 10,
                        "display_top": 20,
                        "display_bottom": 80,
                        "text_color": "#FFCC00",
                    },
                )
                assert updated.status_code == 200
                settings_event = danmaku_ws.receive_json()
                assert settings_event == {
                    "type": "danmaku.settings.updated",
                    "settings": updated.json()["settings"],
                }

                chat_ws.send_json({"type": "message.send", "body": "断线补齐消息"})
                assert chat_ws.receive_json()["type"] == "message.created"
                missed_event = danmaku_ws.receive_json()
                assert missed_event["message"]["body"] == "断线补齐消息"
                second_message_id = missed_event["message"]["message_id"]

                closed = client.post(f"/api/v1/admin/activities/{activity_id}/close", headers=headers)
                assert closed.status_code == 200
                chat_ws.send_json({"type": "message.send", "body": "关闭后不应投放"})
                assert chat_ws.receive_json()["code"] == "read_only"

        missed = client.get(
            f"/api/v1/danmaku/messages?after_id={message_id}",
            headers=danmaku_headers(token),
        )
        assert missed.status_code == 200
        missed_body = missed.json()
        assert missed_body["has_more"] is False
        assert len(missed_body["items"]) == 1
        missed_item = missed_body["items"][0]
        assert set(missed_item) == {"message_id", "activity_id", "body", "created_at"}
        assert missed_item["message_id"] == second_message_id
        assert missed_item["activity_id"] == activity_id
        assert missed_item["body"] == "断线补齐消息"
        assert missed_item["created_at"]
        no_more = client.get(
            f"/api/v1/danmaku/messages?after_id={second_message_id}",
            headers=danmaku_headers(token),
        )
        assert no_more.json() == {"items": [], "has_more": False}
    finally:
        app.dependency_overrides.clear()


def test_admin_danmaku_test_sends_real_chat_messages_to_chat_and_overlay(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    activity_id = ""
    headers: dict[str, str] = {}
    original_interval = danmaku_test_manager.interval_seconds
    original_main_settings = main_module.settings
    danmaku_test_manager.interval_seconds = 0.01
    main_module.settings = settings
    client.__enter__()
    try:
        headers = admin_headers(client)
        activity_id = create_activity(client, headers, "真实聊天室弹幕测试")
        other_activity_id = create_activity(client, headers, "其他活动不应收到测试")
        token = client.get(
            f"/api/v1/admin/activities/{activity_id}/danmaku",
            headers=headers,
        ).json()["token"]
        other_token = client.get(
            f"/api/v1/admin/activities/{other_activity_id}/danmaku",
            headers=headers,
        ).json()["token"]
        user_token = register_user(client, activity_id)
        opened = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
        assert opened.status_code == 200

        with client.websocket_connect("/api/v1/danmaku/ws") as danmaku_ws:
            danmaku_ws.send_json({"type": "auth", "token": token})
            assert danmaku_ws.receive_json()["type"] == "danmaku.ready"
            with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as chat_ws:
                chat_ws.send_json({"type": "auth", "token": user_token})
                assert chat_ws.receive_json()["type"] == "chat.ready"

                started = client.post(
                    f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
                    headers=headers,
                )
                assert started.status_code == 200
                assert started.json() == {"running": True, "detail": "弹幕测试已开启"}

                first_chat = chat_ws.receive_json()
                first_danmaku = danmaku_ws.receive_json()
                assert first_chat["type"] == "message.created"
                assert first_chat["message"]["sender_username"] == "弹幕测试用户1"
                assert first_chat["message"]["activity_id"] == activity_id
                assert first_danmaku["type"] == "danmaku.message.created"
                assert first_danmaku["message"]["message_id"] == first_chat["message"]["message_id"]
                assert first_danmaku["message"]["body"].startswith("【弹幕测试】")

                second_chat = chat_ws.receive_json()
                second_danmaku = danmaku_ws.receive_json()
                assert second_chat["type"] == "message.created"
                assert second_chat["message"]["sender_username"] == "弹幕测试用户2"
                assert second_danmaku["message"]["message_id"] == second_chat["message"]["message_id"]

                already_running = client.post(
                    f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
                    headers=headers,
                )
                assert already_running.status_code == 200
                assert already_running.json() == {"running": True, "detail": "弹幕测试已经在运行"}

                stopped = client.post(
                    f"/api/v1/admin/activities/{activity_id}/danmaku/test/stop",
                    headers=headers,
                )
                assert stopped.status_code == 200
                assert stopped.json() == {"running": False, "detail": "弹幕测试已关闭"}

                restarted = client.post(
                    f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
                    headers=headers,
                )
                assert restarted.status_code == 200
                restarted_chat = None
                for _ in range(TEST_USER_COUNT + 2):
                    candidate_chat = chat_ws.receive_json()
                    candidate_danmaku = danmaku_ws.receive_json()
                    if candidate_chat["message"]["sender_activity_user_id"] == first_chat["message"][
                        "sender_activity_user_id"
                    ]:
                        restarted_chat = candidate_chat
                        assert candidate_danmaku["message"]["message_id"] == candidate_chat["message"]["message_id"]
                        break
                assert restarted_chat is not None
                assert restarted_chat["message"]["sender_username"] == "弹幕测试用户1"
                closed = client.post(f"/api/v1/admin/activities/{activity_id}/close", headers=headers)
                assert closed.status_code == 200
                time.sleep(0.05)
                closed_status = client.get(
                    f"/api/v1/admin/activities/{activity_id}/danmaku/test",
                    headers=headers,
                )
                assert closed_status.status_code == 200
                assert closed_status.json()["running"] is False
                reopened = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
                assert reopened.status_code == 200
                stopped_again = client.post(
                    f"/api/v1/admin/activities/{activity_id}/danmaku/test/stop",
                    headers=headers,
                )
                assert stopped_again.status_code == 200

        history = client.get(
            "/api/v1/danmaku/messages?after_id=0&limit=100",
            headers=danmaku_headers(token),
        )
        assert history.status_code == 200
        items = history.json()["items"]
        assert len(items) >= 2
        assert [items[0]["message_id"], items[1]["message_id"]] == [
            first_chat["message"]["message_id"],
            second_chat["message"]["message_id"],
        ]
        assert {first_chat["message"]["sender_username"], second_chat["message"]["sender_username"]} == {
            "弹幕测试用户1",
            "弹幕测试用户2",
        }
        chat_history = client.get(
            f"/api/v1/activities/{activity_id}/chat/messages?limit=100",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert chat_history.status_code == 200
        history_ids = {item["message_id"] for item in chat_history.json()["items"]}
        assert first_chat["message"]["message_id"] in history_ids
        assert second_chat["message"]["message_id"] in history_ids
        other_status = client.get(
            f"/api/v1/admin/activities/{other_activity_id}/danmaku/test",
            headers=headers,
        )
        assert other_status.status_code == 200
        assert other_status.json()["running"] is False
        other_history = client.get(
            "/api/v1/danmaku/messages?after_id=0&limit=100",
            headers=danmaku_headers(other_token),
        )
        assert other_history.status_code == 200
        assert other_history.json() == {"items": [], "has_more": False}
    finally:
        danmaku_test_manager.interval_seconds = original_interval
        if activity_id and danmaku_test_manager.is_running(activity_id):
            client.post(
                f"/api/v1/admin/activities/{activity_id}/danmaku/test/stop",
                headers=headers,
            )
        client.__exit__(None, None, None)
        main_module.settings = original_main_settings
        app.dependency_overrides.clear()


def test_admin_danmaku_test_requires_open_activity(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        headers = admin_headers(client)
        activity_id = create_activity(client, headers, "未开启活动")
        response = client.post(
            f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "只有进行中的活动可以开启弹幕测试"
        opened = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
        assert opened.status_code == 200
        ended = client.post(f"/api/v1/admin/activities/{activity_id}/end", headers=headers)
        assert ended.status_code == 200
        response = client.post(
            f"/api/v1/admin/activities/{activity_id}/danmaku/test/start",
            headers=headers,
        )
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_admin_danmaku_test_requires_superuser(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        headers = admin_headers(client)
        activity_id = create_activity(client, headers, "管理员权限测试")
        response = client.get(f"/api/v1/admin/activities/{activity_id}/danmaku/test")
        assert response.status_code == 401
        response = client.post(f"/api/v1/admin/activities/{activity_id}/danmaku/test/start")
        assert response.status_code == 401
        response = client.post(f"/api/v1/admin/activities/{activity_id}/danmaku/test/stop")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
