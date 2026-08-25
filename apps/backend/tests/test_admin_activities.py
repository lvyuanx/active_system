from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.core.security import create_access_token, hash_password
from app.main import app


def make_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "test.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    init_database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), settings


def test_superuser_can_login_and_manage_activity(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        login = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret-password"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post(
            "/api/v1/admin/activities",
            headers=headers,
            json={
                "name": "年度大会",
                "description": "年度活动",
                "start_time": "2026-08-10T09:00:00",
                "end_time": "2026-08-10T18:00:00",
            },
        )
        assert created.status_code == 201
        activity = created.json()
        assert activity["status"] == "closed"

        activity_id = activity["activity_id"]
        listed = client.get("/api/v1/admin/activities", headers=headers)
        assert listed.status_code == 200
        assert listed.json()[0]["activity_id"] == activity_id
        opened = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
        assert opened.json()["status"] == "open"
        closed = client.post(f"/api/v1/admin/activities/{activity_id}/close", headers=headers)
        assert closed.json()["status"] == "closed"
        assert client.post(f"/api/v1/admin/activities/{activity_id}/end", headers=headers).json()["status"] == "ended"
        ended_open = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
        assert ended_open.status_code == 400
        missing = client.post("/api/v1/admin/activities/missing/open", headers=headers)
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_admin_api_requires_superuser(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        assert client.get("/api/v1/admin/activities").status_code == 401
        with transaction(settings) as connection:
            connection.execute(
                "INSERT INTO users(username, password_hash, is_superuser, created_at) VALUES (?, ?, 0, ?)",
                ("member", hash_password("member-password"), "2026-08-10T00:00:00+00:00"),
            )
        response = client.post("/api/v1/auth/login", json={"username": "member", "password": "member-password"})
        assert response.status_code == 401
        member_token = create_access_token("member", settings)
        forbidden = client.get(
            "/api/v1/admin/activities",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert forbidden.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_create_activity_validates_time_order(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        login = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret-password"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = client.post(
            "/api/v1/admin/activities",
            headers=headers,
            json={
                "name": "错误时间",
                "start_time": "2026-08-10T18:00:00",
                "end_time": "2026-08-10T09:00:00",
            },
        )
        assert response.status_code == 422
        blank_name = client.post(
            "/api/v1/admin/activities",
            headers=headers,
            json={"name": "   "},
        )
        assert blank_name.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_activity_user_registration_login_and_isolation(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        admin_login = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret-password"})
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        first = client.post("/api/v1/admin/activities", headers=headers, json={"name": "第一场"}).json()
        second = client.post("/api/v1/admin/activities", headers=headers, json={"name": "第二场"}).json()
        public_activity = client.get(f"/api/v1/activities/{first['activity_id']}")
        assert public_activity.status_code == 200
        assert public_activity.json()["name"] == "第一场"

        register = client.post(
            f"/api/v1/activities/{first['activity_id']}/auth/register",
            json={"username": "小明", "phone": "13800000000"},
        )
        assert register.status_code == 201
        user_token = register.json()["access_token"]
        duplicate = client.post(
            f"/api/v1/activities/{first['activity_id']}/auth/register",
            json={"username": "小红", "phone": "13800000000"},
        )
        assert duplicate.status_code == 409
        login = client.post(
            f"/api/v1/activities/{first['activity_id']}/auth/login",
            json={"username": "小明", "phone": "13800000000"},
        )
        assert login.status_code == 200
        me = client.get(
            f"/api/v1/activities/{first['activity_id']}/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert me.status_code == 200 and me.json()["username"] == "小明"
        cross_activity = client.get(
            f"/api/v1/activities/{second['activity_id']}/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert cross_activity.status_code == 403
        other_activity_registration = client.post(
            f"/api/v1/activities/{second['activity_id']}/auth/register",
            json={"username": "小明", "phone": "13800000000"},
        )
        assert other_activity_registration.status_code == 201
    finally:
        app.dependency_overrides.clear()
