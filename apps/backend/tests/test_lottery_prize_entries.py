from pathlib import Path

from app.core.database import transaction
from app.main import app
from app.modules.lottery.service import prepare_lottery_round

from tests.test_lottery import (
    configure_lottery,
    create_activity,
    make_client,
    open_activity,
    register_user,
)


def _entry_url(activity_id: str, prize_id: int, activity_user_id: int | None = None) -> str:
    path = f"/api/v1/admin/activities/{activity_id}/lottery/entries"
    if activity_user_id is not None:
        path += f"/{activity_user_id}"
    return f"{path}?prize_id={prize_id}"


def test_lottery_entries_and_candidates_are_isolated_per_prize(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "奖品独立名单")
        users = [
            register_user(client, activity_id, username, f"1380000500{index}")
            for index, username in enumerate(("奖品甲用户", "奖品乙用户", "公共用户"), start=1)
        ]
        config = configure_lottery(client, activity_id, headers, quantity=1, prize_count=2)
        prize_a = int(config["prizes"][0]["prize_id"])
        prize_b = int(config["prizes"][1]["prize_id"])

        blacklisted = client.put(
            _entry_url(activity_id, prize_a, int(users[0]["activity_user_id"])),
            headers=headers,
            json={"is_blacklisted": True, "is_whitelisted": False},
        )
        whitelisted = client.put(
            _entry_url(activity_id, prize_b, int(users[1]["activity_user_id"])),
            headers=headers,
            json={"is_blacklisted": False, "is_whitelisted": True},
        )
        assert blacklisted.status_code == whitelisted.status_code == 200

        page_a = client.get(_entry_url(activity_id, prize_a), headers=headers)
        page_b = client.get(_entry_url(activity_id, prize_b), headers=headers)
        assert page_a.status_code == page_b.status_code == 200
        assert page_a.json()["prize_id"] == prize_a
        assert page_b.json()["prize_id"] == prize_b
        states_a = {item["username"]: item for item in page_a.json()["items"]}
        states_b = {item["username"]: item for item in page_b.json()["items"]}
        assert states_a["奖品甲用户"]["is_blacklisted"] is True
        assert states_a["奖品乙用户"]["is_whitelisted"] is False
        assert states_b["奖品甲用户"]["is_blacklisted"] is False
        assert states_b["奖品乙用户"]["is_whitelisted"] is True
        assert page_a.json()["summary"] == {
            "total": 3,
            "eligible": 2,
            "blacklisted": 1,
            "whitelisted": 0,
            "inactive": 0,
        }
        assert page_b.json()["summary"] == {
            "total": 3,
            "eligible": 1,
            "blacklisted": 0,
            "whitelisted": 1,
            "inactive": 0,
        }

        open_activity(client, activity_id, headers)
        round_a = prepare_lottery_round(activity_id, prize_a, "prize-a-round", settings)
        round_b = prepare_lottery_round(activity_id, prize_b, "prize-b-round", settings)
        assert round_a.candidate_user_ids == {
            int(users[1]["activity_user_id"]),
            int(users[2]["activity_user_id"]),
        }
        assert round_b.candidate_user_ids == {int(users[1]["activity_user_id"])}

        missing_prize = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries?prize_id=999999",
            headers=headers,
        )
        missing_context = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery/entries",
            headers=headers,
        )
        assert missing_prize.status_code == 404
        assert missing_context.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_legacy_activity_entries_migrate_once_to_existing_prizes(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id, headers = create_activity(client, "旧名单迁移")
        user = register_user(client, activity_id, "历史黑名单", "13800005101")
        config = configure_lottery(client, activity_id, headers, quantity=1, prize_count=2)
        existing_prizes = [int(prize["prize_id"]) for prize in config["prizes"]]

        with transaction(settings) as connection:
            connection.execute(
                "DELETE FROM lottery_prize_entry_migrations WHERE activity_id = ?",
                (activity_id,),
            )
            connection.execute(
                "DELETE FROM lottery_prize_entries WHERE activity_id = ?",
                (activity_id,),
            )
            connection.execute(
                "INSERT INTO lottery_entries("
                "activity_id, activity_user_id, is_blacklisted, is_whitelisted, created_at, updated_at) "
                "VALUES (?, ?, 1, 0, ?, ?)",
                (
                    activity_id,
                    user["activity_user_id"],
                    "2026-08-31T00:00:00+00:00",
                    "2026-08-31T00:00:00+00:00",
                ),
            )

        for prize_id in existing_prizes:
            page = client.get(_entry_url(activity_id, prize_id), headers=headers)
            assert page.status_code == 200
            assert page.json()["summary"]["blacklisted"] == 1
            assert page.json()["items"][0]["is_blacklisted"] is True

        with transaction(settings) as connection:
            connection.execute(
                "UPDATE lottery_entries SET is_blacklisted = 0, is_whitelisted = 1 "
                "WHERE activity_id = ? AND activity_user_id = ?",
                (activity_id, user["activity_user_id"]),
            )
        unchanged = client.get(_entry_url(activity_id, existing_prizes[0]), headers=headers)
        assert unchanged.status_code == 200
        assert unchanged.json()["items"][0]["is_blacklisted"] is True
        assert unchanged.json()["items"][0]["is_whitelisted"] is False

        current = client.get(
            f"/api/v1/admin/activities/{activity_id}/lottery", headers=headers
        ).json()
        current["prizes"].append(
            {
                "prize_id": None,
                "award_id": current["awards"][0]["award_id"],
                "name": "迁移后新奖品",
                "quantity": 1,
                "sort_order": 2,
                "is_enabled": True,
            }
        )
        saved = client.put(
            f"/api/v1/admin/activities/{activity_id}/lottery",
            headers=headers,
            json={
                "awards": current["awards"],
                "prizes": [
                    {
                        key: prize[key]
                        for key in (
                            "prize_id",
                            "award_id",
                            "name",
                            "quantity",
                            "sort_order",
                            "is_enabled",
                        )
                    }
                    for prize in current["prizes"]
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        new_prize_id = int(saved.json()["prizes"][-1]["prize_id"])
        new_page = client.get(_entry_url(activity_id, new_prize_id), headers=headers)
        assert new_page.status_code == 200
        assert new_page.json()["summary"]["blacklisted"] == 0
        assert new_page.json()["items"][0]["is_blacklisted"] is False
    finally:
        app.dependency_overrides.clear()
