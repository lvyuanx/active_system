import json
from pathlib import Path

from app.core.database import transaction
from app.main import app
from app.modules.lottery.round_state import lottery_round_store

from tests.test_lottery import (
    admin_token,
    configure_lottery,
    create_activity,
    make_client,
    open_activity,
    register_user,
)


def _draw_count(settings, activity_id: str) -> int:
    with transaction(settings) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM lottery_draws WHERE activity_id = ?",
            (activity_id,),
        ).fetchone()
    return int(row["count"])


def test_round_starts_animation_without_drawing_and_freezes_pool(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    lottery_round_store.clear_all()
    try:
        activity_id, headers = create_activity(client, "球体抽奖")
        first = register_user(client, activity_id, "可中奖用户", "13800003001")
        blocked = register_user(client, activity_id, "黑名单用户", "13800003002")
        inactive = register_user(client, activity_id, "停用用户", "13800003003")
        config = configure_lottery(
            client,
            activity_id,
            headers,
            quantity=1,
            entries=[
                {
                    "activity_user_id": blocked["activity_user_id"],
                    "is_blacklisted": True,
                    "is_whitelisted": False,
                }
            ],
        )
        deactivated = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/{inactive['activity_user_id']}/deactivate",
            headers=headers,
        )
        assert deactivated.status_code == 200, deactivated.text
        open_activity(client, activity_id, headers)
        prize_id = int(config["prizes"][0]["prize_id"])
        round_id = "round-freeze-001"

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            assert screen.receive_json()["active_round"] is None
            with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                admin.send_json({"type": "auth", "token": admin_token(client)})
                assert admin.receive_json()["active_round"] is None
                admin.send_json({"type": "lottery.draw.start", "round_id": round_id, "prize_id": prize_id})
                admin_started = admin.receive_json()
                screen_started = screen.receive_json()
                assert admin_started["type"] == screen_started["type"] == "lottery.draw.started"
                public_round = screen_started["round"]
                assert public_round["round_id"] == round_id
                assert {item["username"] for item in public_round["participants"]} == {
                    "可中奖用户",
                    "黑名单用户",
                    "停用用户",
                }
                assert all(
                    set(item) == {"activity_user_id", "username", "avatar_id"}
                    for item in public_round["participants"]
                )
                assert "phone" not in json.dumps(screen_started, ensure_ascii=False)
                assert "is_blacklisted" not in json.dumps(screen_started, ensure_ascii=False)
                assert _draw_count(settings, activity_id) == 0

                late = register_user(client, activity_id, "开始后用户", "13800003004")
                blocked_update = client.put(
                    f"/api/v1/admin/activities/{activity_id}/lottery/entries/{first['activity_user_id']}"
                    f"?prize_id={prize_id}",
                    headers=headers,
                    json={"is_blacklisted": True, "is_whitelisted": False},
                )
                assert blocked_update.status_code == 409
                blocked_config = client.put(
                    f"/api/v1/admin/activities/{activity_id}/lottery",
                    headers=headers,
                    json={"rolling_name_count": 12},
                )
                assert blocked_config.status_code == 409

                admin.send_json({"type": "lottery.reset.request"})
                reset_error = admin.receive_json()
                assert reset_error["type"] == "lottery.draw.error"
                assert reset_error["code"] == "draw_in_progress"

                admin.send_json({"type": "lottery.draw.stop", "round_id": round_id, "prize_id": prize_id})
                stopping_admin = admin.receive_json()
                stopping_screen = screen.receive_json()
                assert stopping_admin["type"] == stopping_screen["type"] == "lottery.draw.stopping"
                assert stopping_admin["round_id"] == stopping_screen["round_id"] == round_id
                result = admin.receive_json()
                drawn = screen.receive_json()
                assert result["type"] == "lottery.draw.result"
                assert result["round_id"] == round_id
                assert result["idempotent"] is False
                assert drawn["type"] == "lottery.drawn"
                assert drawn["round_id"] == round_id
                assert drawn["draw"]["winner"]["activity_user_id"] == first["activity_user_id"]
                assert drawn["draw"]["winner"]["activity_user_id"] != late["activity_user_id"]
                first_round_participant = next(
                    item
                    for item in public_round["participants"]
                    if item["activity_user_id"] == first["activity_user_id"]
                )
                assert drawn["draw"]["winner"]["avatar_id"] == first_round_participant["avatar_id"]
                assert _draw_count(settings, activity_id) == 1
    finally:
        lottery_round_store.clear_all()
        app.dependency_overrides.clear()


def test_round_persists_missing_avatar_and_reuses_it_in_public_history(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    lottery_round_store.clear_all()
    try:
        activity_id, headers = create_activity(client, "旧用户头像")
        user = register_user(client, activity_id, "旧头像用户", "13800003005")
        with transaction(settings) as connection:
            connection.execute(
                "UPDATE activity_users SET avatar_id = NULL WHERE activity_id = ? AND id = ?",
                (activity_id, user["activity_user_id"]),
            )
        config = configure_lottery(client, activity_id, headers, quantity=1)
        open_activity(client, activity_id, headers)
        prize_id = int(config["prizes"][0]["prize_id"])
        round_id = "round-avatar-persist-001"

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            screen.receive_json()
            with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                admin.send_json({"type": "auth", "token": admin_token(client)})
                admin.receive_json()
                admin.send_json({"type": "lottery.draw.start", "round_id": round_id, "prize_id": prize_id})
                assert admin.receive_json()["type"] == "lottery.draw.started"
                screen_started = screen.receive_json()
                participant = next(
                    item
                    for item in screen_started["round"]["participants"]
                    if item["activity_user_id"] == user["activity_user_id"]
                )
                assert 1 <= participant["avatar_id"] <= 20
                with transaction(settings) as connection:
                    stored = connection.execute(
                        "SELECT avatar_id FROM activity_users WHERE activity_id = ? AND id = ?",
                        (activity_id, user["activity_user_id"]),
                    ).fetchone()
                assert stored["avatar_id"] == participant["avatar_id"]

                admin.send_json({"type": "lottery.draw.stop", "round_id": round_id, "prize_id": prize_id})
                assert admin.receive_json()["type"] == "lottery.draw.stopping"
                assert screen.receive_json()["type"] == "lottery.draw.stopping"
                result = admin.receive_json()
                drawn = screen.receive_json()
                assert result["type"] == "lottery.draw.result"
                assert drawn["type"] == "lottery.drawn"
                assert drawn["draw"]["winner"]["avatar_id"] == participant["avatar_id"]

            with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as recovered_screen:
                recovered = recovered_screen.receive_json()
                assert recovered["draws"][0]["winner"]["avatar_id"] == participant["avatar_id"]

            with transaction(settings) as connection:
                connection.execute(
                    "UPDATE activity_users SET avatar_id = NULL WHERE activity_id = ? AND id = ?",
                    (activity_id, user["activity_user_id"]),
                )
            with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as legacy_screen:
                legacy_ready = legacy_screen.receive_json()
                legacy_avatar_id = legacy_ready["draws"][0]["winner"]["avatar_id"]
                assert 1 <= legacy_avatar_id <= 20
            with transaction(settings) as connection:
                stored = connection.execute(
                    "SELECT avatar_id FROM activity_users WHERE activity_id = ? AND id = ?",
                    (activity_id, user["activity_user_id"]),
                ).fetchone()
            assert stored["avatar_id"] == legacy_avatar_id
    finally:
        lottery_round_store.clear_all()
        app.dependency_overrides.clear()


def test_round_ready_recovers_and_duplicate_stop_is_idempotent(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    lottery_round_store.clear_all()
    try:
        activity_id, headers = create_activity(client, "球体重连")
        user = register_user(client, activity_id, "重连用户", "13800003101")
        config = configure_lottery(client, activity_id, headers, quantity=1)
        open_activity(client, activity_id, headers)
        prize_id = int(config["prizes"][0]["prize_id"])
        round_id = "round-reconnect-001"

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            screen.receive_json()
            with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                admin.send_json({"type": "auth", "token": admin_token(client)})
                admin.receive_json()
                admin.send_json({"type": "lottery.draw.start", "round_id": round_id, "prize_id": prize_id})
                assert admin.receive_json()["type"] == "lottery.draw.started"
                assert screen.receive_json()["type"] == "lottery.draw.started"
                assert lottery_round_store.mark_stopping(activity_id, round_id) is not None

                with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as recovered_screen:
                    recovered = recovered_screen.receive_json()
                    assert recovered["active_round"]["round_id"] == round_id
                    assert recovered["active_round"]["prize_id"] == prize_id
                    assert recovered["active_round"]["phase"] == "stopping"
                    assert recovered["active_round"]["participants"][0]["username"] == user["username"]

                with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as other_admin:
                    other_admin.send_json({"type": "auth", "token": admin_token(client)})
                    other_ready = other_admin.receive_json()
                    assert other_ready["active_round"]["round_id"] == round_id
                    other_admin.send_json(
                        {"type": "lottery.draw.start", "round_id": "round-conflict-001", "prize_id": prize_id}
                    )
                    conflict = other_admin.receive_json()
                    assert conflict["code"] == "draw_in_progress"
                    assert conflict["round_id"] == "round-conflict-001"
                    admin.send_json(
                        {"type": "lottery.draw.stop", "round_id": round_id, "prize_id": prize_id}
                    )
                    stopping_admin = admin.receive_json()
                    stopping_other_admin = other_admin.receive_json()
                    stopping_screen = screen.receive_json()
                    assert (
                        stopping_admin["type"]
                        == stopping_other_admin["type"]
                        == stopping_screen["type"]
                        == "lottery.draw.stopping"
                    )
                    assert stopping_admin["round_id"] == round_id
                    first_result = admin.receive_json()
                    other_result = other_admin.receive_json()
                    first_drawn = screen.receive_json()
                    assert first_result["type"] == other_result["type"] == "lottery.draw.result"
                    assert first_result["idempotent"] is False
                    assert other_result["idempotent"] is False
                    assert first_drawn["type"] == "lottery.drawn"

                    other_admin.send_json(
                        {"type": "lottery.draw.stop", "round_id": round_id, "prize_id": prize_id}
                    )
                    retry = other_admin.receive_json()
                    assert retry["type"] == "lottery.draw.result"
                    assert retry["idempotent"] is True
                    assert retry["draw"] == other_result["draw"]
                    screen.send_json({"type": "lottery.ping"})
                    assert screen.receive_json() == {"type": "lottery.pong"}
        assert _draw_count(settings, activity_id) == 1
    finally:
        lottery_round_store.clear_all()
        app.dependency_overrides.clear()
