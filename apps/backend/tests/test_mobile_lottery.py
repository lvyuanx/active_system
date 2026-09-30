import json
from pathlib import Path
from time import sleep

from app.main import app
from app.modules.lottery.round_state import lottery_round_store, lottery_selection_store

from tests.test_lottery import (
    admin_token,
    configure_lottery,
    create_activity,
    make_client,
    open_activity,
    register_user,
)


def receive_until(websocket, message_type: str) -> dict:
    while True:
        message = websocket.receive_json()
        if message.get("type") == message_type:
            return message


def test_mobile_lottery_permission_is_activity_scoped_and_reflected_by_me(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "移动抽奖授权")
        other_activity_id, _ = create_activity(client, "其他活动")
        user = register_user(client, activity_id, "授权用户", "13800005001")
        listed = client.get(f"/api/v1/admin/activities/{activity_id}/participants", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["items"][0]["can_mobile_lottery"] is False

        token_headers = {"Authorization": f"Bearer {user['access_token']}"}
        before = client.get(f"/api/v1/activities/{activity_id}/me", headers=token_headers)
        assert before.status_code == 200 and before.json()["can_mobile_lottery"] is False

        granted = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/"
            f"{user['activity_user_id']}/mobile-lottery/grant",
            headers=headers,
        )
        assert granted.status_code == 200
        assert granted.json()["can_mobile_lottery"] is True
        after_grant = client.get(f"/api/v1/activities/{activity_id}/me", headers=token_headers)
        assert after_grant.status_code == 200 and after_grant.json()["can_mobile_lottery"] is True

        cross_activity = client.post(
            f"/api/v1/admin/activities/{other_activity_id}/participants/"
            f"{user['activity_user_id']}/mobile-lottery/grant",
            headers=headers,
        )
        assert cross_activity.status_code == 404

        revoked = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/"
            f"{user['activity_user_id']}/mobile-lottery/revoke",
            headers=headers,
        )
        assert revoked.status_code == 200
        assert revoked.json()["can_mobile_lottery"] is False
        after_revoke = client.get(f"/api/v1/activities/{activity_id}/me", headers=token_headers)
        assert after_revoke.status_code == 200 and after_revoke.json()["can_mobile_lottery"] is False
    finally:
        app.dependency_overrides.clear()


def test_mobile_lottery_controls_the_same_round_as_admin_and_screen(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    lottery_round_store.clear_all()
    lottery_selection_store.clear_all()
    try:
        activity_id, headers = create_activity(client, "移动端开奖")
        operator = register_user(client, activity_id, "移动操作员", "13800005002")
        register_user(client, activity_id, "候选用户", "13800005003")
        config = configure_lottery(client, activity_id, headers, quantity=1, prize_count=2)
        prize_id = int(config["prizes"][0]["prize_id"])
        grant = client.post(
            f"/api/v1/admin/activities/{activity_id}/participants/"
            f"{operator['activity_user_id']}/mobile-lottery/grant",
            headers=headers,
        )
        assert grant.status_code == 200
        open_activity(client, activity_id, headers)

        unauthorized = register_user(client, activity_id, "无权限用户", "13800005004")
        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/mobile/ws") as denied:
            denied.send_json({"type": "auth", "token": unauthorized["access_token"]})
            denied_error = denied.receive_json()
            assert denied_error["type"] == "lottery.draw.error"
            assert denied_error["code"] == "unauthorized"

        with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/ws") as screen:
            assert screen.receive_json()["type"] == "lottery.ready"
            with client.websocket_connect(f"/api/v1/admin/activities/{activity_id}/lottery/ws") as admin:
                admin.send_json({"type": "auth", "token": admin_token(client)})
                assert admin.receive_json()["type"] == "lottery.ready"
                with client.websocket_connect(f"/api/v1/activities/{activity_id}/lottery/mobile/ws") as mobile:
                    mobile.send_json({"type": "auth", "token": operator["access_token"]})
                    mobile_ready = mobile.receive_json()
                    assert mobile_ready["type"] == "lottery.ready"
                    assert "phone" not in json.dumps(mobile_ready, ensure_ascii=False)

                    mobile.send_json({"type": "lottery.prize.select", "prize_id": prize_id})
                    selected_mobile = mobile.receive_json()
                    selected_screen = screen.receive_json()
                    selected_admin = admin.receive_json()
                    assert selected_mobile == selected_screen == selected_admin == {
                        "type": "lottery.prize.selected",
                        "selected_prize_id": prize_id,
                    }

                    round_id = "mobile-round-001"
                    mobile.send_json({"type": "lottery.draw.start", "prize_id": prize_id, "round_id": round_id})
                    started_mobile = mobile.receive_json()
                    started_screen = screen.receive_json()
                    started_admin = admin.receive_json()
                    assert (
                        started_mobile["type"]
                        == started_screen["type"]
                        == started_admin["type"]
                        == "lottery.draw.started"
                    )
                    assert started_mobile["round"]["round_id"] == round_id
                    assert "phone" not in json.dumps(started_mobile, ensure_ascii=False)

                    mobile.send_json({"type": "lottery.draw.stop", "prize_id": prize_id, "round_id": round_id})
                    stopping_mobile = mobile.receive_json()
                    stopping_screen = screen.receive_json()
                    stopping_admin = admin.receive_json()
                    assert stopping_mobile == stopping_screen == stopping_admin == {
                        "type": "lottery.draw.stopping",
                        "request_id": round_id,
                        "round_id": round_id,
                    }

                    sleep(0.05)
                    screen.send_json({"type": "lottery.ping"})
                    screen_result = receive_until(screen, "lottery.drawn")
                    mobile_result = mobile.receive_json()
                    admin_result = admin.receive_json()
                    assert admin_result["type"] == "lottery.draw.result"
                    assert admin_result["round_id"] == round_id
                    assert screen_result["type"] == mobile_result["type"] == "lottery.drawn"
                    assert screen_result["round_id"] == mobile_result["round_id"] == round_id
                    assert set(mobile_result["draw"]["winner"]) == {
                        "activity_user_id",
                        "username",
                        "avatar_id",
                    }
                    assert 1 <= mobile_result["draw"]["winner"]["avatar_id"] <= 20
                    assert "phone" not in json.dumps(screen_result, ensure_ascii=False)
                    assert "phone" not in json.dumps(mobile_result, ensure_ascii=False)

                    mobile.send_json({"type": "lottery.draw.stop", "prize_id": prize_id, "round_id": round_id})
                    retry = mobile.receive_json()
                    assert retry["type"] == "lottery.draw.result"
                    assert retry["idempotent"] is True

                    mobile.send_json(
                        {"type": "lottery.draw.start", "prize_id": prize_id, "round_id": "mobile-round-002"}
                    )
                    exhausted = mobile.receive_json()
                    assert exhausted["type"] == "lottery.draw.error"
                    assert exhausted["code"] == "inventory_exhausted"
    finally:
        lottery_round_store.clear_all()
        lottery_selection_store.clear_all()
        app.dependency_overrides.clear()
