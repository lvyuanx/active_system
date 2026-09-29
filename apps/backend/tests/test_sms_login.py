from pathlib import Path
import importlib

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.main import app
from app.modules.sms.service import SmsProviderError


participants_module = importlib.import_module("app.modules.participants.router")


PHONE = "17343384315"


def make_client(tmp_path: Path, *, sign_name: str = "测试签名") -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "sms-login.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        aliyun_sms_sign_name=sign_name,
        aliyun_sms_template_code="100001",
    )
    init_database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), settings


def create_activity(settings: Settings, activity_id: str = "activity-a") -> None:
    with transaction(settings) as connection:
        connection.execute(
            "INSERT INTO activities(activity_id, name, status, created_at, updated_at) "
            "VALUES (?, ?, 'closed', ?, ?)",
            (activity_id, "短信登录活动", "2026-09-29T00:00:00+00:00", "2026-09-29T00:00:00+00:00"),
        )


def test_existing_phone_logs_in_and_keeps_original_name(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings)
    monkeypatch.setattr(participants_module, "check_sms_code", lambda phone, code, configured: True)
    try:
        registered = client.post(
            "/api/v1/activities/activity-a/auth/register",
            json={"username": "原姓名", "phone": PHONE},
        )
        response = client.post(
            "/api/v1/activities/activity-a/auth/sms-login",
            json={"phone": PHONE, "code": "123456", "username": "新姓名"},
        )
        assert registered.status_code == 201
        assert response.status_code == 200
        assert response.json()["needs_name"] is False
        assert response.json()["user"]["username"] == "原姓名"
        assert response.json()["user"]["access_token"]
    finally:
        app.dependency_overrides.clear()


def test_new_phone_requires_name_before_creating_user(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings)
    monkeypatch.setattr(participants_module, "check_sms_code", lambda phone, code, configured: True)
    try:
        needs_name = client.post(
            "/api/v1/activities/activity-a/auth/sms-login",
            json={"phone": PHONE, "code": "123456"},
        )
        assert needs_name.status_code == 200
        assert needs_name.json() == {"needs_name": True, "user": None}
        with transaction(settings) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM activity_users WHERE activity_id = ? AND phone = ?",
                ("activity-a", PHONE),
            ).fetchone()[0] == 0

        completed = client.post(
            "/api/v1/activities/activity-a/auth/sms-login",
            json={"phone": PHONE, "code": "123456", "username": "新用户"},
        )
        assert completed.status_code == 200
        assert completed.json()["needs_name"] is False
        assert completed.json()["user"]["username"] == "新用户"
        with transaction(settings) as connection:
            assert connection.execute(
                "SELECT username FROM activity_users WHERE activity_id = ? AND phone = ?",
                ("activity-a", PHONE),
            ).fetchone()["username"] == "新用户"
    finally:
        app.dependency_overrides.clear()


def test_sms_login_rejects_invalid_code_without_creating_user(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings)
    monkeypatch.setattr(participants_module, "check_sms_code", lambda phone, code, configured: False)
    try:
        response = client.post(
            "/api/v1/activities/activity-a/auth/sms-login",
            json={"phone": PHONE, "code": "123456", "username": "不应创建"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "验证码错误或已失效"}
        with transaction(settings) as connection:
            assert connection.execute("SELECT COUNT(*) FROM activity_users").fetchone()[0] == 0
    finally:
        app.dependency_overrides.clear()


def test_sms_login_maps_provider_and_configuration_errors(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings)

    def fail_check(phone: str, code: str, configured: Settings) -> bool:
        raise SmsProviderError("provider error")

    monkeypatch.setattr(participants_module, "check_sms_code", fail_check)
    try:
        failed = client.post(
            "/api/v1/activities/activity-a/auth/sms-login",
            json={"phone": PHONE, "code": "123456"},
        )
        assert failed.status_code == 502
        assert failed.json() == {"detail": "短信核验失败，请稍后重试"}

        monkeypatch.undo()
        app.dependency_overrides.clear()
        unavailable_client, unavailable_settings = make_client(tmp_path / "missing", sign_name="")
        create_activity(unavailable_settings)
        unavailable = unavailable_client.post(
            "/api/v1/activities/activity-a/auth/sms-login",
            json={"phone": PHONE, "code": "123456"},
        )
        assert unavailable.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_sms_login_rejects_inactive_existing_user(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings)
    monkeypatch.setattr(participants_module, "check_sms_code", lambda phone, code, configured: True)
    try:
        registered = client.post(
            "/api/v1/activities/activity-a/auth/register",
            json={"username": "停用用户", "phone": PHONE},
        )
        assert registered.status_code == 201
        with transaction(settings) as connection:
            connection.execute(
                "UPDATE activity_users SET is_active = 0 WHERE activity_id = ? AND phone = ?",
                ("activity-a", PHONE),
            )
        response = client.post(
            "/api/v1/activities/activity-a/auth/sms-login",
            json={"phone": PHONE, "code": "123456"},
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "该活动用户已停用"}
    finally:
        app.dependency_overrides.clear()
