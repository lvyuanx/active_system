import sqlite3
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.core.security import create_access_token
from app.main import app


def make_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "participants.db"),
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


def create_activity(client: TestClient, name: str = "参与者活动") -> dict[str, str]:
    response = client.post("/api/v1/admin/activities", headers=admin_headers(client), json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def register_user(client: TestClient, activity_id: str, username: str, phone: str) -> dict:
    response = client.post(
        f"/api/v1/activities/{activity_id}/auth/register",
        json={"username": username, "phone": phone},
    )
    assert response.status_code == 201, response.text
    return response.json()


def open_activity(client: TestClient, activity_id: str) -> None:
    response = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=admin_headers(client))
    assert response.status_code == 200, response.text


def test_admin_lists_and_toggles_participants_with_activity_isolation(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        admin = admin_headers(client)
        first = create_activity(client, "第一场")
        second = create_activity(client, "第二场")
        first_user = register_user(client, first["activity_id"], "小明", "13800000001")
        second_user = register_user(client, second["activity_id"], "小红", "13800000002")
        participant_id = first_user["activity_user_id"]

        unauthorized = client.get(f"/api/v1/admin/activities/{first['activity_id']}/participants")
        assert unauthorized.status_code == 401

        listed = client.get(
            f"/api/v1/admin/activities/{first['activity_id']}/participants",
            headers=admin,
        )
        assert listed.status_code == 200
        assert listed.json() == [
            {
                "activity_id": first["activity_id"],
                "activity_user_id": participant_id,
                "username": "小明",
                "phone": "13800000001",
                "joined_at": first_user["joined_at"],
                "is_active": True,
                "is_muted": False,
            }
        ]

        muted = client.post(
            f"/api/v1/admin/activities/{first['activity_id']}/participants/{participant_id}/mute",
            headers=admin,
        )
        assert muted.status_code == 200 and muted.json()["is_muted"] is True
        unmuted = client.post(
            f"/api/v1/admin/activities/{first['activity_id']}/participants/{participant_id}/unmute",
            headers=admin,
        )
        assert unmuted.status_code == 200 and unmuted.json()["is_muted"] is False

        deactivated = client.post(
            f"/api/v1/admin/activities/{first['activity_id']}/participants/{participant_id}/deactivate",
            headers=admin,
        )
        assert deactivated.status_code == 200 and deactivated.json()["is_active"] is False
        repeated = client.post(
            f"/api/v1/admin/activities/{first['activity_id']}/participants/{participant_id}/deactivate",
            headers=admin,
        )
        assert repeated.status_code == 200 and repeated.json()["is_active"] is False
        activated = client.post(
            f"/api/v1/admin/activities/{first['activity_id']}/participants/{participant_id}/activate",
            headers=admin,
        )
        assert activated.status_code == 200 and activated.json()["is_active"] is True

        cross_activity = client.post(
            f"/api/v1/admin/activities/{second['activity_id']}/participants/{participant_id}/mute",
            headers=admin,
        )
        assert cross_activity.status_code == 404
        assert second_user["activity_id"] != first["activity_id"]

        missing_activity = client.get("/api/v1/admin/activities/missing/participants", headers=admin)
        assert missing_activity.status_code == 404
        missing_user = client.post(
            f"/api/v1/admin/activities/{first['activity_id']}/participants/999999/mute",
            headers=admin,
        )
        assert missing_user.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_muted_participant_can_read_but_cannot_send_until_unmuted(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity = create_activity(client)
        activity_id = activity["activity_id"]
        user = register_user(client, activity_id, "聊天用户", "13800000003")
        open_activity(client, activity_id)
        admin = admin_headers(client)

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": user["access_token"]})
            assert websocket.receive_json()["type"] == "chat.ready"

            muted = client.post(
                f"/api/v1/admin/activities/{activity_id}/participants/"
                f"{user['activity_user_id']}/mute",
                headers=admin,
            )
            assert muted.status_code == 200
            login_while_muted = client.post(
                f"/api/v1/activities/{activity_id}/auth/login",
                json={"username": "聊天用户", "phone": "13800000003"},
            )
            assert login_while_muted.status_code == 200

            websocket.send_json({"type": "message.send", "body": "禁言期间不可发送"})
            assert websocket.receive_json() == {
                "type": "chat.error",
                "code": "muted",
                "detail": "你已被禁言",
            }

            history = client.get(
                f"/api/v1/activities/{activity_id}/chat/messages",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert history.status_code == 200
            assert history.json()["items"] == []

            unmuted = client.post(
                f"/api/v1/admin/activities/{activity_id}/participants/"
                f"{user['activity_user_id']}/unmute",
                headers=admin,
            )
            assert unmuted.status_code == 200
            websocket.send_json({"type": "message.send", "body": "解除禁言后可以发送"})
            created = websocket.receive_json()
            assert created["type"] == "message.created"
            assert created["message"]["body"] == "解除禁言后可以发送"
    finally:
        app.dependency_overrides.clear()


def test_deactivation_invalidates_existing_tokens_and_requires_new_login(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity = create_activity(client)
        activity_id = activity["activity_id"]
        user = register_user(client, activity_id, "停用用户", "13800000004")
        open_activity(client, activity_id)
        admin = admin_headers(client)
        old_token = user["access_token"]
        old_payload = jwt.decode(old_token, settings.jwt_secret, algorithms=["HS256"])
        assert old_payload["activity_user_session_version"] == 0

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": old_token})
            assert websocket.receive_json()["type"] == "chat.ready"

            deactivated = client.post(
                f"/api/v1/admin/activities/{activity_id}/participants/"
                f"{user['activity_user_id']}/deactivate",
                headers=admin,
            )
            assert deactivated.status_code == 200
            assert deactivated.json()["is_active"] is False

            me = client.get(
                f"/api/v1/activities/{activity_id}/me",
                headers={"Authorization": f"Bearer {old_token}"},
            )
            assert me.status_code == 401
            history = client.get(
                f"/api/v1/activities/{activity_id}/chat/messages",
                headers={"Authorization": f"Bearer {old_token}"},
            )
            assert history.status_code == 401
            login = client.post(
                f"/api/v1/activities/{activity_id}/auth/login",
                json={"username": "停用用户", "phone": "13800000004"},
            )
            assert login.status_code == 403

            websocket.send_json({"type": "message.send", "body": "停用后不可发送"})
            assert websocket.receive_json() == {
                "type": "chat.error",
                "code": "unauthorized",
                "detail": "活动登录已失效",
            }
            try:
                websocket.receive_json()
            except WebSocketDisconnect:
                pass

        activated = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/"
            f"{user['activity_user_id']}/activate",
            headers=admin,
        )
        assert activated.status_code == 200
        assert activated.json()["is_active"] is True

        old_token_after_restore = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert old_token_after_restore.status_code == 401

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as blocked_websocket:
            blocked_websocket.send_json({"type": "auth", "token": old_token})
            assert blocked_websocket.receive_json() == {
                "type": "chat.error",
                "code": "unauthorized",
                "detail": "请重新登录活动",
            }
            try:
                blocked_websocket.receive_json()
            except WebSocketDisconnect:
                pass

        new_login = client.post(
            f"/api/v1/activities/{activity_id}/auth/login",
            json={"username": "停用用户", "phone": "13800000004"},
        )
        assert new_login.status_code == 200
        new_token = new_login.json()["access_token"]
        new_payload = jwt.decode(new_token, settings.jwt_secret, algorithms=["HS256"])
        assert new_payload["activity_user_session_version"] == 1
        new_me = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert new_me.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_legacy_activity_user_schema_gets_defaults_and_old_token_is_revoked(tmp_path: Path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "legacy.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    connection = sqlite3.connect(settings.database_path)
    connection.executescript(
        """
        CREATE TABLE activities (
            activity_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE activity_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT NOT NULL,
            username TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TEXT NOT NULL,
            avatar_id INTEGER
        );
        INSERT INTO activities VALUES (
            'legacy-activity', '旧活动', NULL, NULL, NULL, 'open',
            '2026-08-10T00:00:00+00:00', '2026-08-10T00:00:00+00:00'
        );
        INSERT INTO activity_users(activity_id, username, phone, created_at, avatar_id)
        VALUES ('legacy-activity', '旧用户', '13800000005', '2026-08-10T00:00:00+00:00', 1);
        """
    )
    connection.commit()
    connection.close()

    init_database(settings)
    with transaction(settings) as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(activity_users)")}
        defaults = connection.execute(
            "SELECT is_active, is_muted, session_version FROM activity_users WHERE id = 1"
        ).fetchone()
    assert {"is_active", "is_muted", "session_version"} <= columns
    assert tuple(defaults) == (1, 0, 0)

    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        old_token = create_access_token("旧用户", settings, activity_id="legacy-activity", activity_user_id=1)
        legacy_me = client.get(
            "/api/v1/activities/legacy-activity/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert legacy_me.status_code == 200

        admin = admin_headers(client)
        deactivated = client.post(
            "/api/v1/admin/activities/legacy-activity/participants/1/deactivate",
            headers=admin,
        )
        assert deactivated.status_code == 200
        activated = client.post(
            "/api/v1/admin/activities/legacy-activity/participants/1/activate",
            headers=admin,
        )
        assert activated.status_code == 200
        revoked_legacy_me = client.get(
            "/api/v1/activities/legacy-activity/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert revoked_legacy_me.status_code == 401
    finally:
        app.dependency_overrides.clear()
