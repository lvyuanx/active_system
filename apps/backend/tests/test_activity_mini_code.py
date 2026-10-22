import json
import importlib
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database
from app.main import app
from app.modules.activities import mini_code


activities_router_module = importlib.import_module("app.modules.activities.router")


ACTIVITY_ID = "79d30a1a-47ef-42d0-a90d-c02768784a25"


def make_client(tmp_path: Path, *, configured: bool = True) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "test.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
        wechat_miniapp_appid="wx-test-appid" if configured else "",
        wechat_miniapp_secret="test-secret" if configured else "",
    )
    init_database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), settings


def admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret-password"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_mini_code_endpoint_returns_png_for_admin(tmp_path: Path, monkeypatch) -> None:
    client, _ = make_client(tmp_path)
    try:
        headers = admin_headers(client)
        created = client.post(
            "/api/v1/admin/activities",
            headers=headers,
            json={"name": "小程序码测试活动"},
        )
        assert created.status_code == 201
        activity_id = created.json()["activity_id"]

        called: list[str] = []

        def fake_generate(requested_id: str, _settings: Settings) -> bytes:
            called.append(requested_id)
            return b"fake-png"

        monkeypatch.setattr(activities_router_module, "generate_mini_program_code", fake_generate)
        response = client.get(f"/api/v1/admin/activities/{activity_id}/mini-code", headers=headers)

        assert response.status_code == 200
        assert response.content == b"fake-png"
        assert response.headers["content-type"] == "image/png"
        assert response.headers["cache-control"] == "private, max-age=300"
        assert called == [activity_id]
    finally:
        app.dependency_overrides.clear()


def test_mini_code_endpoint_requires_configuration(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path, configured=False)
    try:
        headers = admin_headers(client)
        created = client.post(
            "/api/v1/admin/activities",
            headers=headers,
            json={"name": "未配置测试活动"},
        )
        activity_id = created.json()["activity_id"]
        response = client.get(f"/api/v1/admin/activities/{activity_id}/mini-code", headers=headers)
        assert response.status_code == 503
        assert "WECHAT_MINIAPP_SECRET" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_generate_mini_program_code_passes_activity_query(monkeypatch) -> None:
    mini_code._token_cache.clear()
    calls: list[Request] = []
    responses = [
        b'{"access_token":"access-token-1","expires_in":7200}',
        b"fake-png",
    ]

    class FakeResponse:
        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    def fake_urlopen(request: Request, timeout: int) -> FakeResponse:
        assert timeout == 10
        calls.append(request)
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr(mini_code, "urlopen", fake_urlopen)
    settings = Settings(
        wechat_miniapp_appid="wx-test-appid",
        wechat_miniapp_secret="test-secret",
    )

    result = mini_code.generate_mini_program_code(ACTIVITY_ID, settings)

    assert result == b"fake-png"
    assert parse_qs(urlparse(calls[0].full_url).query)["appid"] == ["wx-test-appid"]
    payload = json.loads(calls[1].data.decode("utf-8"))
    assert payload == {"path": f"pages/entry/index?activity_id={ACTIVITY_ID}", "width": 430}
    assert parse_qs(urlparse(calls[1].full_url).query)["access_token"] == ["access-token-1"]
