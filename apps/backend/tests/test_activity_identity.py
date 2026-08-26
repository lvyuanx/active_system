from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database
from app.core.security import create_access_token
from app.main import app


def make_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "identity.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    init_database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), settings


def create_activity(client: TestClient) -> str:
    login = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret-password"})
    response = client.post(
        "/api/v1/admin/activities",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"name": "身份测试"},
    )
    return response.json()["activity_id"]


def test_old_token_fallback_requires_unique_username_and_rejects_invalid_claim(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id = create_activity(client)
        register = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "旧用户", "phone": "13800000001"},
        )
        assert register.status_code == 201
        old_token = create_access_token("旧用户", settings, activity_id=activity_id)
        me = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert me.status_code == 200

        duplicate = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "旧用户", "phone": "13800000002"},
        )
        assert duplicate.status_code == 201
        ambiguous = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert ambiguous.status_code == 401

        expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        for invalid_claim in ("1", True, None):
            invalid_token = jwt.encode(
                {
                    "sub": "旧用户",
                    "activity_id": activity_id,
                    "activity_user_id": invalid_claim,
                    "exp": expiry,
                },
                settings.jwt_secret,
                algorithm="HS256",
            )
            response = client.get(
                f"/api/v1/activities/{activity_id}/me",
                headers={"Authorization": f"Bearer {invalid_token}"},
            )
            assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
