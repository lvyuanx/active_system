from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.lottery.manager import lottery_manager
from app.modules.lottery.round_state import lottery_selection_store
from app.modules.lottery.service import LotteryDrawError, draw_lottery


def make_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / "lottery.db"),
        media_root=str(tmp_path / "media"),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        lottery_security_code="",
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


def admin_token(client: TestClient) -> str:
    return admin_headers(client)["Authorization"].split(" ", 1)[1]


def create_activity(client: TestClient, name: str = "抽奖活动") -> tuple[str, dict[str, str]]:
    headers = admin_headers(client)
    response = client.post("/api/v1/admin/activities", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["activity_id"], headers


def register_user(client: TestClient, activity_id: str, username: str, phone: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/activities/{activity_id}/auth/register",
        json={"username": username, "phone": phone},
    )
    assert response.status_code == 201, response.text
    return response.json()


def configure_lottery(
    client: TestClient,
    activity_id: str,
    headers: dict[str, str],
    *,
    quantity: int = 1,
    entries: list[dict[str, object]] | None = None,
    no_repeat: bool = True,
    prize_count: int = 1,
) -> dict[str, object]:
    current = client.get(f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers)
    assert current.status_code == 200, current.text
    config = current.json()
    award = config["awards"][0]
    prizes = [
        {
            "prize_id": config["prizes"][0]["prize_id"],
            "award_id": award["award_id"],
            "name": "无线耳机" if index == 0 else f"备用奖品{index + 1}",
            "quantity": quantity,
            "sort_order": index,
            "is_enabled": True,
        }
        for index in range(prize_count)
    ]
    for index in range(1, prize_count):
        prizes[index]["prize_id"] = None
    payload = {
        "no_repeat_across_prizes": no_repeat,
        "rolling_name_count": 8,
        "awards": [
            {"award_id": award["award_id"], "name": "三等奖", "sort_order": 0},
        ],
        "prizes": prizes,
    }
    response = client.put(
        f"/api/v1/admin/activities/{activity_id}/lottery",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200, response.text
    config = response.json()
    for entry in entries or []:
        for prize in config["prizes"]:
            entry_response = client.put(
                f"/api/v1/admin/activities/{activity_id}/lottery/entries/{entry['activity_user_id']}"
                f"?prize_id={prize['prize_id']}",
                headers=headers,
                json={
                    "is_blacklisted": entry.get("is_blacklisted", False),
                    "is_whitelisted": entry.get("is_whitelisted", False),
                },
            )
            assert entry_response.status_code == 200, entry_response.text
    return config


def open_activity(client: TestClient, activity_id: str, headers: dict[str, str]) -> None:
    response = client.post(f"/api/v1/admin/activities/{activity_id}/open", headers=headers)
    assert response.status_code == 200, response.text


def test_lottery_config_and_history_are_activity_isolated(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        first_id, headers = create_activity(client, "第一场抽奖")
        second_id, _ = create_activity(client, "第二场抽奖")
        first_user = register_user(client, first_id, "小明", "13800001001")
        first_config = configure_lottery(client, first_id, headers, quantity=2)

        first = client.get(f"/api/v1/admin/activities/{first_id}/lottery", headers=headers)
        second = client.get(f"/api/v1/admin/activities/{second_id}/lottery", headers=headers)
        assert first.status_code == second.status_code == 200
        assert first.json()["activity_id"] == first_id
        assert second.json()["activity_id"] == second_id
        assert "entries" not in first.json()
        first_prize_id = first_config["prizes"][0]["prize_id"]
        second_prize_id = second.json()["prizes"][0]["prize_id"]
        first_entries = client.get(
            f"/api/v1/admin/activities/{first_id}/lottery/entries?prize_id={first_prize_id}",
            headers=headers,
        )
        second_entries = client.get(
            f"/api/v1/admin/activities/{second_id}/lottery/entries?prize_id={second_prize_id}",
            headers=headers,
        )
        assert first_entries.json()["items"][0]["activity_user_id"] == first_user["activity_user_id"]
        assert first_entries.json()["summary"]["total"] == 1
        assert second_entries.json()["items"] == []
        assert second_entries.json()["summary"]["total"] == 0

        history = client.get(f"/api/v1/admin/activities/{first_id}/lottery/history", headers=headers)
        assert history.status_code == 200
        assert history.json() == {"items": [], "has_more": False}
        forbidden = client.get(
            f"/api/v1/admin/activities/{first_id}/lottery",
            headers={"Authorization": "Bearer invalid"},
        )
        assert forbidden.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_lottery_entries_support_search_filters_pagination_and_activity_isolation(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "名单分页")
        other_activity_id, _ = create_activity(client, "其他活动")
        users = [
            register_user(client, activity_id, f"用户{index}", f"138000020{index:02d}")
            for index in range(5)
        ]
        register_user(client, other_activity_id, "其他用户", "13800002999")
        config = configure_lottery(client, activity_id, headers, quantity=2)
        prize_id = config["prizes"][0]["prize_id"]

        for user, flags in (
            (users[0], {"is_blacklisted": True, "is_whitelisted": False}),
            (users[1], {"is_blacklisted": False, "is_whitelisted": True}),
        ):
            response = client.put(
                f"/api/v1/admin/activities/{activity_id}/lottery/entries/{user['activity_user_id']}"
                f"?prize_id={prize_id}",
                headers=headers,
                json=flags,
            )
            assert response.status_code == 200, response.text
        deactivated = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/{users[4]['activity_user_id']}/deactivate",
            headers=headers,
        )
        assert deactivated.status_code == 200, deactivated.text

        page = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries?prize_id={prize_id}&page=1&page_size=2",
            headers=headers,
        )
        assert page.status_code == 200, page.text
        assert len(page.json()["items"]) == 2
        assert page.json()["total"] == 5
        assert page.json()["has_more"] is True
        assert page.json()["summary"] == {
            "total": 5,
            "eligible": 1,
            "blacklisted": 1,
            "whitelisted": 1,
            "inactive": 1,
        }

        by_username = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries?prize_id={prize_id}"
            "&keyword=%E7%94%A8%E6%88%B73",
            headers=headers,
        )
        assert [item["username"] for item in by_username.json()["items"]] == ["用户3"]
        by_phone = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries?prize_id={prize_id}&keyword=02002",
            headers=headers,
        )
        assert [item["username"] for item in by_phone.json()["items"]] == ["用户2"]

        expected_filters = {
            "blacklisted": "用户0",
            "whitelisted": "用户1",
            "inactive": "用户4",
            "eligible": "用户1",
        }
        for status_filter, expected_username in expected_filters.items():
            response = client.get(
                f"/api/v1/admin/activities/{activity_id}/lottery/entries"
                f"?prize_id={prize_id}&status={status_filter}",
                headers=headers,
            )
            assert [item["username"] for item in response.json()["items"]] == [expected_username]

        other_config = client.get(
            f"/api/v1/admin/activities/{other_activity_id}/lottery", headers=headers
        ).json()
        other_prize_id = other_config["prizes"][0]["prize_id"]
        isolated = client.get(
            f"/api/v1/admin/activities/{other_activity_id}/lottery/entries?prize_id={other_prize_id}",
            headers=headers,
        )
        assert [item["username"] for item in isolated.json()["items"]] == ["其他用户"]
        unauthenticated = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries?prize_id={prize_id}"
        )
        assert unauthenticated.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_lottery_security_code_verification_is_server_side_and_activity_scoped(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "特殊配置验证")
        not_configured = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/security-code/verify",
            headers=headers,
            json={"security_code": "lottery-pass"},
        )
        assert not_configured.status_code == 503

        settings.lottery_security_code = "lottery-pass"
        unauthenticated = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/security-code/verify",
            json={"security_code": "lottery-pass"},
        )
        assert unauthenticated.status_code == 401

        invalid = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/security-code/verify",
            headers=headers,
            json={"security_code": "wrong-pass"},
        )
        assert invalid.status_code == 403
        assert "lottery-pass" not in invalid.text

        valid = client.post(
            f"/api/v1/admin/activities/{activity_id}/lottery/security-code/verify",
            headers=headers,
            json={"security_code": "lottery-pass"},
        )
        assert valid.status_code == 200
        assert valid.json() == {"verified": True}

        missing_activity = client.post(
            "/api/v1/admin/activities/missing/lottery/security-code/verify",
            headers=headers,
            json={"security_code": "lottery-pass"},
        )
        assert missing_activity.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_lottery_entry_updates_are_incremental_and_validate_flags(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "名单即时保存")
        first = register_user(client, activity_id, "第一位", "13800002101")
        second = register_user(client, activity_id, "第二位", "13800002102")
        config = configure_lottery(client, activity_id, headers, quantity=2)
        prize_id = config["prizes"][0]["prize_id"]

        first_update = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries/{first['activity_user_id']}"
            f"?prize_id={prize_id}",
            headers=headers,
            json={"is_blacklisted": True, "is_whitelisted": False},
        )
        second_update = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries/{second['activity_user_id']}"
            f"?prize_id={prize_id}",
            headers=headers,
            json={"is_blacklisted": False, "is_whitelisted": True},
        )
        assert first_update.status_code == second_update.status_code == 200
        assert first_update.json()["entry"]["is_blacklisted"] is True
        assert second_update.json()["entry"]["is_whitelisted"] is True
        assert second_update.json()["summary"]["blacklisted"] == 1
        assert second_update.json()["summary"]["whitelisted"] == 1

        invalid = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries/{first['activity_user_id']}"
            f"?prize_id={prize_id}",
            headers=headers,
            json={"is_blacklisted": True, "is_whitelisted": True},
        )
        assert invalid.status_code == 422

        config_update = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery",
            headers=headers,
            json={"rolling_name_count": 12},
        )
        assert config_update.status_code == 200, config_update.text

        entries = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries?prize_id={prize_id}",
            headers=headers,
        ).json()["items"]
        states = {entry["username"]: entry for entry in entries}
        assert states["第一位"]["is_blacklisted"] is True
        assert states["第二位"]["is_whitelisted"] is True

        missing = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries/999999?prize_id={prize_id}",
            headers=headers,
            json={"is_blacklisted": True, "is_whitelisted": False},
        )
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_admin_and_public_websockets_authenticate_and_keep_public_payload_safe(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client)
        user = register_user(client, activity_id, "小明", "13800001002")
        configure_lottery(client, activity_id, headers, quantity=1)
        open_activity(client, activity_id, headers)
        token = admin_token(client)

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            ready = screen.receive_json()
            assert ready["type"] == "lottery.ready"
            assert ready["activity_id"] == activity_id
            assert "entries" not in json.dumps(ready, ensure_ascii=False)
            assert "phone" not in json.dumps(ready, ensure_ascii=False)
            screen.send_json({"type": "lottery.draw.request", "prize_id": 1, "request_id": "screen-write"})
            read_only = screen.receive_json()
            assert read_only["type"] == "lottery.draw.error"
            assert read_only["code"] == "read_only"

            with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                admin.send_json({"type": "auth", "token": token})
                admin_ready = admin.receive_json()
                assert admin_ready["type"] == "lottery.ready"
                assert admin_ready["activity_id"] == activity_id
                admin.send_json({"type": "lottery.ping"})
                assert admin.receive_json() == {"type": "lottery.pong"}

        with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as bad_admin:
            bad_admin.send_json({"type": "auth", "token": user["access_token"]})
            error = bad_admin.receive_json()
            assert error["type"] == "lottery.draw.error"
            assert error["code"] == "unauthorized"

        with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as raw_admin:
            raw_admin.send_text(token)
            assert raw_admin.receive_json()["type"] == "lottery.ready"

        member_username = "member"
        with transaction(settings) as connection:
            connection.execute(
                "INSERT INTO users(username, password_hash, is_superuser, created_at) VALUES (?, ?, 0, ?)",
                (member_username, hash_password("member-password"), "2026-08-28T00:00:00+00:00"),
            )
        member_token = create_access_token(member_username, settings)
        with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as member_ws:
            member_ws.send_json({"type": "auth", "token": member_token})
            assert member_ws.receive_json()["code"] == "unauthorized"

        second_id, _ = create_activity(client, "另一个活动")
        with client.websocket_connect(f"/api/v1/admin/activities/{second_id}/lottery/ws") as cross_activity:
            cross_activity.send_json({"type": "auth", "token": user["access_token"]})
            assert cross_activity.receive_json()["code"] == "unauthorized"
    finally:
        app.dependency_overrides.clear()


def test_draw_commits_before_broadcast_and_request_retry_is_idempotent(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client)
        user = register_user(client, activity_id, "小明", "13800001003")
        config = configure_lottery(client, activity_id, headers, quantity=1)
        prize_id = config["prizes"][0]["prize_id"]
        open_activity(client, activity_id, headers)
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            assert screen.receive_json()["type"] == "lottery.ready"
            with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                admin.send_json({"type": "auth", "token": admin_token(client)})
                assert admin.receive_json()["type"] == "lottery.ready"
                with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as other_admin:
                    other_admin.send_json({"type": "auth", "token": admin_token(client)})
                    assert other_admin.receive_json()["type"] == "lottery.ready"
                    request = {"type": "lottery.draw.request", "prize_id": prize_id, "request_id": "req-001"}
                    admin.send_json(request)
                    result = admin.receive_json()
                    other_result = other_admin.receive_json()
                    drawn = screen.receive_json()
                assert result["type"] == "lottery.draw.result"
                assert other_result == result
                assert result["idempotent"] is False
                assert result["draw"]["winner"]["activity_user_id"] == user["activity_user_id"]
                assert drawn["type"] == "lottery.drawn"
                assert drawn["draw"] == {
                    key: result["draw"][key]
                    for key in result["draw"]
                    if key != "winner"
                } | {"winner": {"activity_user_id": user["activity_user_id"], "username": "小明"}}
                assert "phone" not in json.dumps(drawn, ensure_ascii=False)
                admin.send_json(request)
                retry = admin.receive_json()
                assert retry["type"] == "lottery.draw.result"
                assert retry["idempotent"] is True
                assert retry["draw"] == result["draw"]
            with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as reconnected_screen:
                recovered = reconnected_screen.receive_json()
                assert recovered["type"] == "lottery.ready"
                assert [draw["draw_id"] for draw in recovered["draws"]] == [result["draw"]["draw_id"]]
        with transaction(settings) as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM lottery_draws WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()["count"]
        assert count == 1
        history = client.get(f"/api/v1/admin/activities/{activity_id}/lottery/history", headers=headers)
        assert history.json()["items"][0]["winner"]["phone"] == "13800001003"
    finally:
        app.dependency_overrides.clear()


def test_concurrent_draws_never_exceed_quantity(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client)
        for index in range(6):
            register_user(client, activity_id, f"用户{index}", f"138000011{index:02d}")
        config = configure_lottery(client, activity_id, headers, quantity=2)
        prize_id = int(config["prizes"][0]["prize_id"])
        open_activity(client, activity_id, headers)

        def run_draw(index: int):
            try:
                return draw_lottery(activity_id, prize_id, f"concurrent-{index}", settings)
            except LotteryDrawError as error:
                return error

        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(run_draw, range(6)))
        successes = [result for result in results if not isinstance(result, LotteryDrawError)]
        failures = [result for result in results if isinstance(result, LotteryDrawError)]
        assert len(successes) == 2
        assert all(error.code == "inventory_exhausted" for error in failures)
        with transaction(settings) as connection:
            rows = connection.execute(
                "SELECT COUNT(*) AS count, MIN(draw_number) AS first_number, MAX(draw_number) AS last_number "
                "FROM lottery_draws WHERE activity_id = ? AND prize_id = ?",
                (activity_id, prize_id),
            ).fetchone()
        assert dict(rows) == {"count": 2, "first_number": 1, "last_number": 2}
    finally:
        app.dependency_overrides.clear()


def test_eligibility_rules_reset_and_error_events(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client)
        eligible = register_user(client, activity_id, "白名单用户", "13800001201")
        blocked = register_user(client, activity_id, "黑名单用户", "13800001202")
        inactive = register_user(client, activity_id, "停用用户", "13800001203")
        entries = [
            {
                "activity_user_id": eligible["activity_user_id"],
                "is_whitelisted": True,
                "is_blacklisted": False,
            },
            {
                "activity_user_id": blocked["activity_user_id"],
                "is_whitelisted": False,
                "is_blacklisted": True,
            },
            {
                "activity_user_id": inactive["activity_user_id"],
                "is_whitelisted": True,
                "is_blacklisted": False,
            },
        ]
        config = configure_lottery(
            client,
            activity_id,
            headers,
            quantity=1,
            entries=entries,
            prize_count=2,
        )
        first_prize = int(config["prizes"][0]["prize_id"])
        second_prize = int(config["prizes"][1]["prize_id"])
        deactivate = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/{inactive['activity_user_id']}/deactivate",
            headers=headers,
        )
        assert deactivate.status_code == 200
        open_activity(client, activity_id, headers)
        first = draw_lottery(activity_id, first_prize, "eligibility-1", settings)
        assert first.draw.winner["activity_user_id"] == eligible["activity_user_id"]
        try:
            draw_lottery(activity_id, second_prize, "eligibility-2", settings)
        except LotteryDrawError as error:
            assert error.code == "no_eligible_winner"
        else:
            raise AssertionError("跨奖品不重复规则未生效")

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            ready = screen.receive_json()
            assert len(ready["draws"]) == 1
            with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                admin.send_json({"type": "auth", "token": admin_token(client)})
                assert admin.receive_json()["type"] == "lottery.ready"
                admin.send_json(
                    {"type": "lottery.draw.request", "prize_id": second_prize, "request_id": "error-001"}
                )
                error = admin.receive_json()
                assert error["type"] == "lottery.draw.error"
                assert error["code"] == "no_eligible_winner"

                admin.send_json({"type": "lottery.reset.request"})
                reset_admin = admin.receive_json()
                reset_screen = screen.receive_json()
                assert reset_admin["type"] == reset_screen["type"] == "lottery.reset"
                assert reset_admin["snapshot"]["draws"] == []
                assert reset_screen["snapshot"]["draws"] == []
                assert "phone" not in json.dumps(reset_screen, ensure_ascii=False)
        with transaction(settings) as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM lottery_draws WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()["count"]
        assert count == 0
    finally:
        app.dependency_overrides.clear()


def test_config_update_broadcasts_safe_event_only_to_same_activity(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        first_id, headers = create_activity(client, "配置同步一")
        second_id, second_headers = create_activity(client, "配置同步二")
        configure_lottery(client, first_id, headers, quantity=3)
        configure_lottery(client, second_id, second_headers, quantity=3)
        with client.websocket_connect(f"/api/v1/activities/{first_id}/lottery/ws") as first_screen:
            assert first_screen.receive_json()["type"] == "lottery.ready"
            with client.websocket_connect(f"/api/v1/activities/{second_id}/lottery/ws") as second_screen:
                assert second_screen.receive_json()["type"] == "lottery.ready"
                config = client.get(f"/api/v1/admin/activities/{first_id}/lottery", headers=headers).json()
                response = client.put(
                    f"/api/v1/admin/activities/{first_id}/lottery",
                    headers=headers,
                    json={"rolling_name_count": 12},
                )
                assert response.status_code == 200
                event = first_screen.receive_json()
                assert event["type"] == "lottery.config.updated"
                assert event["config"]["rolling_name_count"] == 12
                assert "entries" not in event["config"]
                assert "phone" not in json.dumps(event, ensure_ascii=False)
                assert config["activity_id"] == first_id
                second_screen.send_json({"type": "lottery.ping"})
                assert second_screen.receive_json() == {"type": "lottery.pong"}
    finally:
        app.dependency_overrides.clear()


def test_selected_prize_broadcasts_and_recovers_on_screen_reconnect(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "当前奖品同步")
        config = configure_lottery(client, activity_id, headers, quantity=2, prize_count=2)
        open_activity(client, activity_id, headers)
        selected_prize_id = config["prizes"][1]["prize_id"]
        second_id, second_headers = create_activity(client, "当前奖品隔离")
        configure_lottery(client, second_id, second_headers, quantity=2, prize_count=2)
        open_activity(client, second_id, second_headers)

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            initial_ready = screen.receive_json()
            assert initial_ready["selected_prize_id"] is None
            with client.websocket_connect(f"/api/v1/activities/{second_id}/lottery/ws") as second_screen:
                assert second_screen.receive_json()["selected_prize_id"] is None
                with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                    admin.send_json({"type": "auth", "token": admin_token(client)})
                    assert admin.receive_json()["type"] == "lottery.ready"
                    admin.send_json({"type": "lottery.prize.select", "prize_id": selected_prize_id})

                    admin_event = admin.receive_json()
                    screen_event = screen.receive_json()
                    assert admin_event == screen_event == {
                        "type": "lottery.prize.selected",
                        "selected_prize_id": selected_prize_id,
                    }
                    second_screen.send_json({"type": "lottery.ping"})
                    assert second_screen.receive_json() == {"type": "lottery.pong"}

                    with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as recovered:
                        recovered_ready = recovered.receive_json()
                        assert recovered_ready["selected_prize_id"] == selected_prize_id
    finally:
        lottery_selection_store.clear_all()
        app.dependency_overrides.clear()


def test_lottery_disconnect_cleans_activity_room(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "断开清理")
        configure_lottery(client, activity_id, headers)
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            assert screen.receive_json()["type"] == "lottery.ready"
            assert activity_id in lottery_manager._rooms
            assert len(lottery_manager._rooms[activity_id]) == 1
        assert activity_id not in lottery_manager._rooms
    finally:
        app.dependency_overrides.clear()
