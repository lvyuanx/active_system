import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.main import app
from app.modules.sms import service as sms_service


PHONE = "17343384315"


def make_client(tmp_path: Path, *, sign_name: str = "测试签名") -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "sms.db"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        aliyun_sms_sign_name=sign_name,
        aliyun_sms_template_code="100001",
    )
    init_database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), settings


def create_activity(settings: Settings, activity_id: str) -> None:
    with transaction(settings) as connection:
        connection.execute(
            "INSERT INTO activities(activity_id, name, status, created_at, updated_at) "
            "VALUES (?, ?, 'closed', ?, ?)",
            (activity_id, "短信测试活动", "2026-09-29T00:00:00+00:00", "2026-09-29T00:00:00+00:00"),
        )


def test_send_sms_code_returns_safe_response_and_expected_parameters(
    tmp_path: Path, monkeypatch
) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings, "activity-a")
    calls: list[tuple[str, Settings]] = []
    monkeypatch.setattr(
        sms_service,
        "_send_via_aliyun",
        lambda phone, configured: calls.append((phone, configured)),
    )
    try:
        response = client.post(
            "/api/v1/activities/activity-a/auth/sms-code",
            json={"phone": f"  {PHONE} "},
        )
        assert response.status_code == 200
        assert response.json() == {
            "message": "验证码发送成功",
            "expires_in": 300,
            "retry_after": 60,
        }
        assert calls == [(PHONE, settings)]
        assert "##code##" not in response.text

        queries = sms_service.build_sms_queries(PHONE, settings)
        assert queries["CountryCode"] == "86"
        assert queries["PhoneNumber"] == PHONE
        assert queries["Interval"] == 60
        assert queries["CodeLength"] == 6
        assert queries["ValidTime"] == 300
        assert queries["ReturnVerifyCode"] is False
        assert json.loads(queries["TemplateParam"]) == {"code": "##code##", "min": "5"}
    finally:
        app.dependency_overrides.clear()


def test_sms_rate_limit_is_global_across_activities(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings, "activity-a")
    create_activity(settings, "activity-b")
    monkeypatch.setattr(sms_service, "_send_via_aliyun", lambda phone, configured: None)
    try:
        first = client.post(
            "/api/v1/activities/activity-a/auth/sms-code",
            json={"phone": PHONE},
        )
        limited = client.post(
            "/api/v1/activities/activity-b/auth/sms-code",
            json={"phone": PHONE},
        )
        other_phone = client.post(
            "/api/v1/activities/activity-b/auth/sms-code",
            json={"phone": "17343384316"},
        )
        assert first.status_code == 200
        assert limited.status_code == 429
        assert limited.headers["Retry-After"] == "60"
        assert other_phone.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_sms_rate_limit_survives_settings_reload(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings, "activity-a")
    monkeypatch.setattr(sms_service, "_send_via_aliyun", lambda phone, configured: None)
    try:
        assert client.post(
            "/api/v1/activities/activity-a/auth/sms-code",
            json={"phone": PHONE},
        ).status_code == 200

        app.dependency_overrides.clear()
        reloaded = Settings(
            database_path=settings.database_path,
            jwt_secret=settings.jwt_secret,
            aliyun_sms_sign_name="测试签名",
            aliyun_sms_template_code="100001",
        )
        init_database(reloaded)
        app.dependency_overrides[get_settings] = lambda: reloaded
        response = client.post(
            "/api/v1/activities/activity-a/auth/sms-code",
            json={"phone": PHONE},
        )
        assert response.status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_concurrent_sms_reservations_allow_only_one(tmp_path: Path) -> None:
    _, settings = make_client(tmp_path)

    def reserve() -> str:
        try:
            sms_service.reserve_sms_send(PHONE, settings)
        except sms_service.SmsRateLimitError:
            return "limited"
        return "reserved"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: reserve(), range(2)))
        assert sorted(results) == ["limited", "reserved"]
    finally:
        app.dependency_overrides.clear()


def test_check_sms_code_builds_provider_request_and_maps_pass(
    tmp_path: Path, monkeypatch
) -> None:
    _, settings = make_client(tmp_path)
    settings.aliyun_sms_scheme_name = "测试方案"
    from alibabacloud_tea_openapi.client import Client as OpenApiClient

    calls: list[dict[str, object]] = []

    def fake_call(client, params, request, runtime):
        calls.append(
            {
                "action": params.action,
                "phone": request.query["PhoneNumber"],
                "code": request.query["VerifyCode"],
                "country_code": request.query["CountryCode"],
                "scheme_name": request.query["SchemeName"],
            }
        )
        return {"body": {"Code": "OK", "Success": True, "Model": {"VerifyResult": "PASS"}}}

    monkeypatch.setattr(OpenApiClient, "call_api", fake_call)
    try:
        assert sms_service.check_sms_code(PHONE, "123456", settings) is True
        assert calls == [
            {
                "action": "CheckSmsVerifyCode",
                "phone": PHONE,
                "code": "123456",
                "country_code": "86",
                "scheme_name": "测试方案",
            }
        ]
        queries = sms_service.build_check_sms_queries(PHONE, "123456", settings)
        assert queries == {
            "CountryCode": "86",
            "PhoneNumber": PHONE,
            "VerifyCode": "123456",
            "SchemeName": "测试方案",
        }
    finally:
        app.dependency_overrides.clear()


def test_verify_sms_route_maps_pass_and_unknown_without_local_rate_limit(
    tmp_path: Path, monkeypatch
) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings, "activity-a")
    monkeypatch.setattr(
        sms_service,
        "_check_via_aliyun",
        lambda phone, code, configured: code == "123456",
    )
    try:
        passed = client.post(
            "/api/v1/activities/activity-a/auth/sms-code/verify",
            json={"phone": f" {PHONE} ", "code": " 123456 "},
        )
        unknown = client.post(
            "/api/v1/activities/activity-a/auth/sms-code/verify",
            json={"phone": PHONE, "code": "654321"},
        )
        assert passed.status_code == 200
        assert passed.json() == {"verified": True, "message": "验证码校验成功"}
        assert unknown.status_code == 200
        assert unknown.json() == {"verified": False, "message": "验证码错误或已失效"}
    finally:
        app.dependency_overrides.clear()


def test_verify_sms_route_rejects_invalid_input_and_unknown_activity(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        invalid_phone = client.post(
            "/api/v1/activities/missing/auth/sms-code/verify",
            json={"phone": "123", "code": "123456"},
        )
        invalid_code = client.post(
            "/api/v1/activities/missing/auth/sms-code/verify",
            json={"phone": PHONE, "code": "abc"},
        )
        missing_activity = client.post(
            "/api/v1/activities/missing/auth/sms-code/verify",
            json={"phone": PHONE, "code": "123456"},
        )
        assert invalid_phone.status_code == 422
        assert invalid_code.status_code == 422
        assert missing_activity.status_code == 404
        with transaction(settings) as connection:
            count = connection.execute("SELECT COUNT(*) FROM sms_verification_sends").fetchone()[0]
        assert count == 0
    finally:
        app.dependency_overrides.clear()


def test_verify_sms_route_hides_provider_errors_and_missing_configuration(
    tmp_path: Path, monkeypatch
) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings, "activity-a")

    def fail_check(phone: str, code: str, configured: Settings) -> bool:
        raise sms_service.SmsProviderError("provider response leaked")

    monkeypatch.setattr(sms_service, "_check_via_aliyun", fail_check)
    try:
        failed = client.post(
            "/api/v1/activities/activity-a/auth/sms-code/verify",
            json={"phone": PHONE, "code": "123456"},
        )
        assert failed.status_code == 502
        assert failed.json() == {"detail": "短信核验失败，请稍后重试"}
        assert "provider response leaked" not in failed.text

        app.dependency_overrides.clear()
        unavailable_client, unavailable_settings = make_client(tmp_path / "missing", sign_name="")
        create_activity(unavailable_settings, "activity-a")
        unavailable = unavailable_client.post(
            "/api/v1/activities/activity-a/auth/sms-code/verify",
            json={"phone": PHONE, "code": "123456"},
        )
        assert unavailable.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_sms_code_rejects_invalid_phone_and_unknown_activity(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        invalid = client.post(
            "/api/v1/activities/missing/auth/sms-code",
            json={"phone": "123"},
        )
        missing = client.post(
            "/api/v1/activities/missing/auth/sms-code",
            json={"phone": PHONE},
        )
        assert invalid.status_code == 422
        assert missing.status_code == 404
        with transaction(settings) as connection:
            count = connection.execute("SELECT COUNT(*) FROM sms_verification_sends").fetchone()[0]
        assert count == 0
    finally:
        app.dependency_overrides.clear()


def test_sms_code_returns_unavailable_when_configuration_is_missing(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path, sign_name="")
    create_activity(settings, "activity-a")
    try:
        response = client.post(
            "/api/v1/activities/activity-a/auth/sms-code",
            json={"phone": PHONE},
        )
        assert response.status_code == 503
        with transaction(settings) as connection:
            count = connection.execute("SELECT COUNT(*) FROM sms_verification_sends").fetchone()[0]
        assert count == 0
    finally:
        app.dependency_overrides.clear()


def test_provider_failure_keeps_the_rate_limit_reservation(tmp_path: Path, monkeypatch) -> None:
    client, settings = make_client(tmp_path)
    create_activity(settings, "activity-a")

    def fail_send(phone: str, configured: Settings) -> None:
        raise sms_service.SmsProviderError("provider failed")

    monkeypatch.setattr(sms_service, "_send_via_aliyun", fail_send)
    try:
        failed = client.post(
            "/api/v1/activities/activity-a/auth/sms-code",
            json={"phone": PHONE},
        )
        retry = client.post(
            "/api/v1/activities/activity-a/auth/sms-code",
            json={"phone": PHONE},
        )
        assert failed.status_code == 502
        assert failed.json() == {"detail": "短信发送失败，请稍后重试"}
        assert retry.status_code == 429
    finally:
        app.dependency_overrides.clear()
