from pathlib import Path

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.core.database import init_database
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


def test_websocket_malformed_json_returns_structured_error(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        admin_token = client.post(
            "/api/v1/auth/login", json={"username": "root", "password": "secret-password"}
        ).json()["access_token"]
        activity = client.post(
            "/api/v1/admin/activities",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "协议测试"},
        ).json()
        activity_id = activity["activity_id"]
        client.post(
            f"/api/v1/admin/activities/{activity_id}/open",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        token = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "协议用户", "phone": "13800000003"},
        ).json()["access_token"]
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_text("{")
            assert websocket.receive_json()["type"] == "chat.error"
            try:
                websocket.receive_json()
            except WebSocketDisconnect:
                pass

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/chat/ws") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            assert websocket.receive_json()["type"] == "chat.ready"
            websocket.send_text("{")
            assert websocket.receive_json() == {
                "type": "chat.error",
                "code": "protocol_error",
                "detail": "消息必须是合法 JSON",
            }
            websocket.send_json({"type": "unknown"})
            assert websocket.receive_json()["type"] == "chat.error"
    finally:
        app.dependency_overrides.clear()
