from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.core.security import create_access_token
from app.main import app


def make_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "chat.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
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


def create_activity(client: TestClient, *, name: str = "聊天活动") -> tuple[str, dict[str, str]]:
    response = client.post("/api/v1/admin/activities", headers=admin_headers(client), json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["activity_id"], admin_headers(client)


def register_user(client: TestClient, activity_id: str, username: str, phone: str) -> str:
    response = client.post(
        f"/api/v1/activities/{activity_id}/auth/register",
        json={"username": username, "phone": phone},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def open_activity(client: TestClient, activity_id: str, headers: dict[str, str]) -> None:
    response = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
    assert response.status_code == 200, response.text


def test_chat_websocket_broadcast_persists_and_supports_history(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, admin = create_activity(client)
        alice = register_user(client, activity_id, "小明", "13800000001")
        bob = register_user(client, activity_id, "小红", "13800000002")
        open_activity(client, activity_id, admin)

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as ws_alice:
            ws_alice.send_json({"type": "auth", "token": alice})
            ready_alice = ws_alice.receive_json()
            assert ready_alice["type"] == "chat.ready"
            with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as ws_bob:
                ws_bob.send_json({"type": "auth", "token": bob})
                assert ws_bob.receive_json()["type"] == "chat.ready"

                ws_alice.send_json({"type": "message.send", "body": "  大家好  "})
                alice_message = ws_alice.receive_json()
                bob_message = ws_bob.receive_json()
                assert alice_message == bob_message
                assert alice_message["type"] == "message.created"
                message = alice_message["message"]
                assert message["body"] == "大家好"
                assert message["sender_username"] == "小明"
                assert message["sender_activity_user_id"] == ready_alice["activity_user_id"]
                assert message["activity_id"] == activity_id
                assert message["created_at"]
                message_id = message["message_id"]

        history = client.get(
            f"/api/v1/activities/{activity_id}/chat/messages",
            headers={"Authorization": f"Bearer {alice}"},
        )
        assert history.status_code == 200
        assert history.json()["items"][0]["message_id"] == message_id
        assert history.json()["has_more"] is False
    finally:
        app.dependency_overrides.clear()


def test_chat_history_cursor_pagination_and_cross_activity_isolation(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        first_id, admin = create_activity(client, name="第一活动")
        second_id, _ = create_activity(client, name="第二活动")
        first_token = register_user(client, first_id, "用户一", "13800000101")
        second_token = register_user(client, second_id, "用户二", "13800000102")
        open_activity(client, first_id, admin)

        with client.websocket_connect(f"/api/v1/activities/{first_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": first_token})
            assert websocket.receive_json()["type"] == "chat.ready"
            message_ids: list[int] = []
            for body in ("第一条", "第二条", "第三条"):
                websocket.send_json({"type": "message.send", "body": body})
                message_ids.append(websocket.receive_json()["message"]["message_id"])

        page = client.get(
            f"/api/v1/activities/{first_id}/chat/messages?limit=2",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert page.status_code == 200
        assert [item["message_id"] for item in page.json()["items"]] == message_ids[1:]
        assert page.json()["has_more"] is True

        before = client.get(
            f"/api/v1/activities/{first_id}/chat/messages?limit=1&before_id={message_ids[2]}",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert before.status_code == 200
        assert [item["message_id"] for item in before.json()["items"]] == [message_ids[1]]
        assert before.json()["has_more"] is True

        after = client.get(
            f"/api/v1/activities/{first_id}/chat/messages?limit=2&after_id={message_ids[0]}",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert after.status_code == 200
        assert [item["message_id"] for item in after.json()["items"]] == message_ids[1:]

        both_cursors = client.get(
            f"/api/v1/activities/{first_id}/chat/messages?before_id=1&after_id=1",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert both_cursors.status_code == 422

        cross_http = client.get(
            f"/api/v1/activities/{second_id}/chat/messages",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert cross_http.status_code == 403

        with client.websocket_connect(f"/api/v1/activities/{second_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": first_token})
            error = websocket.receive_json()
            assert error["type"] == "chat.error"
            assert error["code"] == "unauthorized"
    finally:
        app.dependency_overrides.clear()


def test_chat_closed_and_ended_are_read_only(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, admin = create_activity(client)
        token = register_user(client, activity_id, "只读用户", "13800000201")
        open_activity(client, activity_id, admin)

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "chat.ready"
            websocket.send_json({"type": "message.send", "body": "可见历史"})
            created = websocket.receive_json()["message"]

        closed = client.post(f"/api/v1/admin/activities/{activity_id}/close", headers=admin)
        assert closed.status_code == 200
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "chat.ready"
            websocket.send_json({"type": "message.send", "body": "关闭后不可发言"})
            assert websocket.receive_json() == {
                "type": "chat.error",
                "code": "read_only",
                "detail": "当前活动暂不可发言",
            }
        history = client.get(
            f"/api/v1/activities/{activity_id}/chat/messages",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert [item["message_id"] for item in history.json()["items"]] == [created["message_id"]]

        ended = client.post(f"/api/v1/admin/activities/{activity_id}/end", headers=admin)
        assert ended.status_code == 200
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "chat.ready"
            websocket.send_json({"type": "message.send", "body": "结束后不可发言"})
            assert websocket.receive_json()["code"] == "read_only"
    finally:
        app.dependency_overrides.clear()


def test_chat_rejects_invalid_protocol_and_body_without_persisting(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, admin = create_activity(client)
        token = register_user(client, activity_id, "校验用户", "13800000301")
        open_activity(client, activity_id, admin)
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "wrong", "token": token})
            protocol_error = websocket.receive_json()
            assert protocol_error["code"] == "protocol_error"

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "chat.ready"
            websocket.send_json({"type": "message.send", "body": "   "})
            assert websocket.receive_json()["code"] == "invalid_body"
            websocket.send_json({"type": "message.send", "body": "x" * 501})
            assert websocket.receive_json()["code"] == "invalid_body"
            websocket.send_json({"type": "message.send", "body": 123})
            assert websocket.receive_json()["code"] == "invalid_body"
            websocket.send_json({"type": "unknown"})
            assert websocket.receive_json()["code"] == "protocol_error"

        history = client.get(
            f"/api/v1/activities/{activity_id}/chat/messages",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert history.status_code == 200
        assert history.json()["items"] == []
    finally:
        app.dependency_overrides.clear()


def test_chat_legacy_token_requires_unique_username_and_stable_ids_for_duplicates(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, _ = create_activity(client)
        duplicate_one = register_user(client, activity_id, "重名", "13800000401")
        duplicate_two = register_user(client, activity_id, "重名", "13800000402")
        unique = register_user(client, activity_id, "唯一", "13800000403")

        duplicate_ids = {
            client.get(
                f"/api/v1/activities/{activity_id}/me",
                headers={"Authorization": f"Bearer {token}"},
            ).json()["activity_user_id"]
            for token in (duplicate_one, duplicate_two)
        }
        assert len(duplicate_ids) == 2

        legacy_duplicate = create_access_token("重名", settings, activity_id=activity_id)
        rejected = client.get(
            f"/api/v1/activities/{activity_id}/chat/messages",
            headers={"Authorization": f"Bearer {legacy_duplicate}"},
        )
        assert rejected.status_code == 401

        legacy_unique = create_access_token("唯一", settings, activity_id=activity_id)
        accepted = client.get(
            f"/api/v1/activities/{activity_id}/chat/messages",
            headers={"Authorization": f"Bearer {legacy_unique}"},
        )
        assert accepted.status_code == 200
        assert accepted.json() == {"items": [], "has_more": False}
    finally:
        app.dependency_overrides.clear()
