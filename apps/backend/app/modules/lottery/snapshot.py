from typing import Any
import sqlite3

from app.core.config import Settings
from app.core.database import transaction
from .models import LotteryConfigResponse
from .repository import activity_or_raise, admin_draw, draw_row, ensure_config, prize_image_url, public_draw


def _snapshot_from_connection(
    connection: sqlite3.Connection,
    activity_id: str,
    *,
    include_sensitive: bool,
) -> dict[str, Any]:
    activity = activity_or_raise(connection, activity_id)
    config = ensure_config(connection, activity_id)
    rows = connection.execute(
        "SELECT draw_id FROM lottery_draws WHERE activity_id = ? ORDER BY draw_id ASC",
        (activity_id,),
    ).fetchall()
    all_draws = [draw_row(connection, int(row["draw_id"])) for row in rows]
    draw_models = [admin_draw(row) if include_sensitive else public_draw(row) for row in all_draws]
    awards = connection.execute(
        "SELECT award_id, name, sort_order FROM lottery_awards WHERE activity_id = ? "
        "ORDER BY sort_order, award_id",
        (activity_id,),
    ).fetchall()
    award_snapshots: list[dict[str, Any]] = []
    for award in awards:
        prizes = connection.execute(
            """SELECT p.prize_id, p.award_id, p.name, p.quantity, p.sort_order, p.is_enabled, p.image_id,
                      p.quantity - COUNT(d.draw_id) AS remaining_quantity
                 FROM lottery_prizes p
                 LEFT JOIN lottery_draws d ON d.prize_id = p.prize_id AND d.activity_id = p.activity_id
                WHERE p.activity_id = ? AND p.award_id = ? GROUP BY p.prize_id
                ORDER BY p.sort_order, p.prize_id""",
            (activity_id, int(award["award_id"])),
        ).fetchall()
        award_draws = [
            draw.model_dump(mode="json")
            for draw in draw_models
            if draw.award_id == int(award["award_id"])
        ]
        award_snapshots.append(
            {
                "award_id": int(award["award_id"]),
                "name": str(award["name"]),
                "sort_order": int(award["sort_order"]),
                "prizes": [
                    {
                        "prize_id": int(prize["prize_id"]),
                        "award_id": int(prize["award_id"]),
                        "name": str(prize["name"]),
                        "quantity": int(prize["quantity"]),
                        "remaining_quantity": int(prize["remaining_quantity"]),
                        "sort_order": int(prize["sort_order"]),
                        "is_enabled": bool(prize["is_enabled"]),
                        "image_url": prize_image_url(
                            activity_id,
                            int(prize["prize_id"]),
                            prize["image_id"],
                        ),
                    }
                    for prize in prizes
                ],
                "draws": award_draws,
            }
        )
    return {
        "activity_id": activity_id,
        "activity_name": str(activity["name"]),
        "activity_status": str(activity["status"]),
        "config": {
            "no_repeat_across_prizes": bool(config["no_repeat_across_prizes"]),
            "rolling_name_count": int(config["rolling_name_count"]),
        },
        "awards": award_snapshots,
        "draws": [draw.model_dump(mode="json") for draw in draw_models],
        "latest_draw_id": int(all_draws[-1]["draw_id"]) if all_draws else 0,
    }


def get_lottery_snapshot(
    activity_id: str,
    settings: Settings,
    *,
    include_sensitive: bool,
) -> dict[str, Any]:
    with transaction(settings) as connection:
        return _snapshot_from_connection(connection, activity_id, include_sensitive=include_sensitive)


def reset_lottery(activity_id: str, settings: Settings) -> dict[str, Any]:
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        activity_or_raise(connection, activity_id)
        connection.execute("DELETE FROM lottery_draws WHERE activity_id = ?", (activity_id,))
        return _snapshot_from_connection(connection, activity_id, include_sensitive=True)


def public_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """从管理员快照中移除名单和中奖手机号，供公开广播使用。"""
    safe_awards: list[dict[str, Any]] = []
    for award in snapshot.get("awards", []):
        if not isinstance(award, dict):
            continue
        safe_awards.append({key: value for key, value in award.items() if key != "draws"})
        safe_awards[-1]["draws"] = [
            _public_draw_from_dict(draw)
            for draw in award.get("draws", [])
            if isinstance(draw, dict)
        ]
    safe_draws = [
        _public_draw_from_dict(draw)
        for draw in snapshot.get("draws", [])
        if isinstance(draw, dict)
    ]
    return {**snapshot, "awards": safe_awards, "draws": safe_draws}


def _public_draw_from_dict(draw: dict[str, Any]) -> dict[str, Any]:
    winner = draw.get("winner")
    safe_winner: dict[str, Any] = {}
    if isinstance(winner, dict):
        for key in ("activity_user_id", "username"):
            if key in winner:
                safe_winner[key] = winner[key]
    return {
        key: draw[key]
        for key in (
            "draw_id",
            "activity_id",
            "award_id",
            "prize_id",
            "award_name",
            "prize_name",
            "draw_number",
            "remaining_quantity",
            "prize_image_url",
            "drawn_at",
        )
        if key in draw
    } | {"winner": safe_winner}


def public_config(config: LotteryConfigResponse) -> dict[str, Any]:
    return {
        "activity_id": config.activity_id,
        "no_repeat_across_prizes": config.no_repeat_across_prizes,
        "rolling_name_count": config.rolling_name_count,
        "awards": [award.model_dump(mode="json") for award in config.awards],
        "prizes": [prize.model_dump(mode="json") for prize in config.prizes],
        "updated_at": config.updated_at.isoformat(),
    }
