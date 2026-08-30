from datetime import datetime, timezone
import sqlite3
from urllib.parse import quote

from .models import (
    LotteryAward,
    LotteryConfigError,
    LotteryConfigResponse,
    LotteryEntry,
    LotteryEntryStatus,
    LotteryEntrySummary,
    LotteryDrawAdmin,
    LotteryDrawError,
    LotteryDrawPublic,
    LotteryPrize,
)


DEFAULT_LOTTERY_CONFIG = {
    "no_repeat_across_prizes": True,
    "rolling_name_count": 8,
}
DEFAULT_AWARD_NAME = "一等奖"
DEFAULT_PRIZE_NAME = "默认奖品"


def prize_image_url(activity_id: str, prize_id: int, image_id: str | None) -> str | None:
    if not image_id:
        return None
    safe_activity_id = quote(activity_id, safe="")
    return f"/api/v1/activities/{safe_activity_id}/lottery/prizes/{prize_id}/image?v={quote(image_id, safe='')}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def activity_or_raise(connection: sqlite3.Connection, activity_id: str) -> sqlite3.Row:
    activity = connection.execute(
        "SELECT activity_id, name, status FROM activities WHERE activity_id = ?",
        (activity_id,),
    ).fetchone()
    if not activity:
        raise LotteryConfigError("activity_not_found", "活动不存在")
    return activity


def ensure_config(connection: sqlite3.Connection, activity_id: str) -> sqlite3.Row:
    activity_or_raise(connection, activity_id)
    current_time = now()
    connection.execute(
        "INSERT OR IGNORE INTO lottery_configs(activity_id, no_repeat_across_prizes, rolling_name_count, updated_at) "
        "VALUES (?, ?, ?, ?)",
        (
            activity_id,
            int(DEFAULT_LOTTERY_CONFIG["no_repeat_across_prizes"]),
            DEFAULT_LOTTERY_CONFIG["rolling_name_count"],
            current_time,
        ),
    )
    award = connection.execute(
        "SELECT award_id FROM lottery_awards WHERE activity_id = ? "
        "ORDER BY sort_order, award_id LIMIT 1",
        (activity_id,),
    ).fetchone()
    if not award:
        cursor = connection.execute(
            "INSERT INTO lottery_awards(activity_id, name, sort_order) VALUES (?, ?, 0)",
            (activity_id, DEFAULT_AWARD_NAME),
        )
        award_id = int(cursor.lastrowid)
    else:
        award_id = int(award["award_id"])
    prize = connection.execute(
        "SELECT prize_id FROM lottery_prizes WHERE activity_id = ? LIMIT 1",
        (activity_id,),
    ).fetchone()
    if not prize:
        connection.execute(
            "INSERT INTO lottery_prizes(activity_id, award_id, name, quantity, sort_order, is_enabled) "
            "VALUES (?, ?, ?, 1, 0, 1)",
            (activity_id, award_id, DEFAULT_PRIZE_NAME),
        )
    row = connection.execute(
        "SELECT * FROM lottery_configs WHERE activity_id = ?", (activity_id,)
    ).fetchone()
    if not row:
        raise LotteryConfigError("config_error", "抽奖配置初始化失败")
    return row


def prize_rows(connection: sqlite3.Connection, activity_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """SELECT p.prize_id, p.award_id, p.name, p.quantity, p.sort_order, p.is_enabled,
                  p.image_id, p.image_storage_key, p.image_mime, p.image_size,
                  p.quantity - COUNT(d.draw_id) AS remaining_quantity
           FROM lottery_prizes p
           LEFT JOIN lottery_draws d ON d.prize_id = p.prize_id AND d.activity_id = p.activity_id
          WHERE p.activity_id = ?
          GROUP BY p.prize_id
          ORDER BY p.sort_order, p.prize_id""",
        (activity_id,),
    ).fetchall()


def entry_where(
    connection: sqlite3.Connection,
    activity_id: str,
    *,
    status: LotteryEntryStatus,
    keyword: str | None,
    no_repeat: bool,
) -> tuple[str, list[object]]:
    clauses = ["u.activity_id = ?"]
    parameters: list[object] = [activity_id]
    if status == "eligible":
        has_whitelist = connection.execute(
            "SELECT 1 FROM lottery_entries WHERE activity_id = ? AND is_whitelisted = 1 LIMIT 1",
            (activity_id,),
        ).fetchone()
        clauses.extend(
            [
                "u.is_active = 1",
                "COALESCE(e.is_blacklisted, 0) = 0",
                "(? = 0 OR COALESCE(e.is_whitelisted, 0) = 1)",
            ]
        )
        parameters.append(int(bool(has_whitelist)))
        if no_repeat:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM lottery_draws previous "
                "WHERE previous.activity_id = u.activity_id AND previous.activity_user_id = u.id)"
            )
    elif status == "blacklisted":
        clauses.append("COALESCE(e.is_blacklisted, 0) = 1")
    elif status == "whitelisted":
        clauses.append("COALESCE(e.is_whitelisted, 0) = 1")
    elif status == "inactive":
        clauses.append("u.is_active = 0")
    if keyword:
        clauses.append("(u.username LIKE ? OR u.phone LIKE ?)")
        pattern = f"%{keyword}%"
        parameters.extend([pattern, pattern])
    return " AND ".join(clauses), parameters


def lottery_entry_row(
    connection: sqlite3.Connection,
    activity_id: str,
    activity_user_id: int,
) -> sqlite3.Row:
    row = connection.execute(
        """SELECT u.id AS activity_user_id, u.username, u.phone, u.is_active,
                  COALESCE(e.is_blacklisted, 0) AS is_blacklisted,
                  COALESCE(e.is_whitelisted, 0) AS is_whitelisted
             FROM activity_users u
             LEFT JOIN lottery_entries e
               ON e.activity_id = u.activity_id AND e.activity_user_id = u.id
            WHERE u.activity_id = ? AND u.id = ?""",
        (activity_id, activity_user_id),
    ).fetchone()
    if not row:
        raise LotteryConfigError("entry_not_found", "参与者不存在或不属于当前活动")
    return row


def lottery_entry(row: sqlite3.Row) -> LotteryEntry:
    return LotteryEntry(
        activity_user_id=int(row["activity_user_id"]),
        username=str(row["username"]),
        phone=str(row["phone"]),
        is_active=bool(row["is_active"]),
        is_blacklisted=bool(row["is_blacklisted"]),
        is_whitelisted=bool(row["is_whitelisted"]),
    )


def lottery_entry_rows(
    connection: sqlite3.Connection,
    activity_id: str,
    *,
    status: LotteryEntryStatus,
    keyword: str | None,
    no_repeat: bool,
    limit: int,
    offset: int,
) -> tuple[list[sqlite3.Row], int]:
    where, parameters = entry_where(
        connection,
        activity_id,
        status=status,
        keyword=keyword,
        no_repeat=no_repeat,
    )
    from_clause = (
        "FROM activity_users u "
        "LEFT JOIN lottery_entries e "
        "ON e.activity_id = u.activity_id AND e.activity_user_id = u.id"
    )
    count_row = connection.execute(
        f"SELECT COUNT(*) AS total {from_clause} WHERE {where}",
        parameters,
    ).fetchone()
    rows = connection.execute(
        f"""SELECT u.id AS activity_user_id, u.username, u.phone, u.is_active,
                  COALESCE(e.is_blacklisted, 0) AS is_blacklisted,
                  COALESCE(e.is_whitelisted, 0) AS is_whitelisted
             {from_clause}
            WHERE {where}
            ORDER BY u.created_at DESC, u.id DESC
            LIMIT ? OFFSET ?""",
        (*parameters, limit, offset),
    ).fetchall()
    return rows, int(count_row["total"])


def lottery_entry_summary(
    connection: sqlite3.Connection,
    activity_id: str,
    *,
    no_repeat: bool,
) -> LotteryEntrySummary:
    row = connection.execute(
        """SELECT COUNT(*) AS total,
                  COALESCE(SUM(CASE WHEN COALESCE(e.is_blacklisted, 0) = 1 THEN 1 ELSE 0 END), 0)
                      AS blacklisted,
                  COALESCE(SUM(CASE WHEN COALESCE(e.is_whitelisted, 0) = 1 THEN 1 ELSE 0 END), 0)
                      AS whitelisted,
                  COALESCE(SUM(CASE WHEN u.is_active = 0 THEN 1 ELSE 0 END), 0) AS inactive
             FROM activity_users u
             LEFT JOIN lottery_entries e
               ON e.activity_id = u.activity_id AND e.activity_user_id = u.id
            WHERE u.activity_id = ?""",
        (activity_id,),
    ).fetchone()
    eligible_where, eligible_parameters = entry_where(
        connection,
        activity_id,
        status="eligible",
        keyword=None,
        no_repeat=no_repeat,
    )
    eligible_row = connection.execute(
        """SELECT COUNT(*) AS total
             FROM activity_users u
             LEFT JOIN lottery_entries e
               ON e.activity_id = u.activity_id AND e.activity_user_id = u.id
            WHERE """ + eligible_where,
        eligible_parameters,
    ).fetchone()
    return LotteryEntrySummary(
        total=int(row["total"]),
        eligible=int(eligible_row["total"]),
        blacklisted=int(row["blacklisted"]),
        whitelisted=int(row["whitelisted"]),
        inactive=int(row["inactive"]),
    )


def config_response(connection: sqlite3.Connection, activity_id: str) -> LotteryConfigResponse:
    config = ensure_config(connection, activity_id)
    awards = connection.execute(
        "SELECT award_id, name, sort_order FROM lottery_awards WHERE activity_id = ? "
        "ORDER BY sort_order, award_id",
        (activity_id,),
    ).fetchall()
    return LotteryConfigResponse(
        activity_id=activity_id,
        no_repeat_across_prizes=bool(config["no_repeat_across_prizes"]),
        rolling_name_count=int(config["rolling_name_count"]),
        awards=[
            LotteryAward(
                award_id=int(row["award_id"]),
                name=str(row["name"]),
                sort_order=int(row["sort_order"]),
            )
            for row in awards
        ],
        prizes=[
            LotteryPrize(
                prize_id=int(row["prize_id"]),
                award_id=int(row["award_id"]),
                name=str(row["name"]),
                quantity=int(row["quantity"]),
                remaining_quantity=int(row["remaining_quantity"]),
                sort_order=int(row["sort_order"]),
                is_enabled=bool(row["is_enabled"]),
                image_url=prize_image_url(activity_id, int(row["prize_id"]), row["image_id"]),
            )
            for row in prize_rows(connection, activity_id)
        ],
        entry_summary=lottery_entry_summary(
            connection,
            activity_id,
            no_repeat=bool(config["no_repeat_across_prizes"]),
        ),
        updated_at=datetime.fromisoformat(str(config["updated_at"])),
    )


def draw_count(connection: sqlite3.Connection, activity_id: str, prize_id: int) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM lottery_draws WHERE activity_id = ? AND prize_id = ?",
        (activity_id, prize_id),
    ).fetchone()
    return int(row["count"])


def draw_row(connection: sqlite3.Connection, draw_id: int) -> sqlite3.Row:
    row = connection.execute(
        """SELECT d.draw_id, d.activity_id, d.award_id, d.prize_id, a.name AS award_name,
                  p.name AS prize_name, p.image_id, d.draw_number, p.quantity -
                  (SELECT COUNT(*) FROM lottery_draws d2 WHERE d2.activity_id = d.activity_id
                   AND d2.prize_id = d.prize_id) AS remaining_quantity,
                  d.request_id, d.drawn_at, u.id AS activity_user_id, u.username, u.phone, u.created_at
             FROM lottery_draws d
             JOIN lottery_awards a ON a.award_id = d.award_id AND a.activity_id = d.activity_id
             JOIN lottery_prizes p ON p.prize_id = d.prize_id AND p.activity_id = d.activity_id
             JOIN activity_users u ON u.id = d.activity_user_id AND u.activity_id = d.activity_id
            WHERE d.draw_id = ?""",
        (draw_id,),
    ).fetchone()
    if not row:
        raise LotteryDrawError("draw_not_found", "中奖记录不存在")
    return row


def admin_draw(row: sqlite3.Row) -> LotteryDrawAdmin:
    return LotteryDrawAdmin(
        draw_id=int(row["draw_id"]),
        activity_id=str(row["activity_id"]),
        award_id=int(row["award_id"]),
        prize_id=int(row["prize_id"]),
        award_name=str(row["award_name"]),
        prize_name=str(row["prize_name"]),
        draw_number=int(row["draw_number"]),
        remaining_quantity=int(row["remaining_quantity"]),
        prize_image_url=prize_image_url(str(row["activity_id"]), int(row["prize_id"]), row["image_id"]),
        winner={
            "activity_user_id": int(row["activity_user_id"]),
            "username": str(row["username"]),
            "phone": str(row["phone"]),
            "joined_at": str(row["created_at"]),
        },
        drawn_at=datetime.fromisoformat(str(row["drawn_at"])),
    )


def public_draw(row: sqlite3.Row) -> LotteryDrawPublic:
    return LotteryDrawPublic(
        draw_id=int(row["draw_id"]),
        activity_id=str(row["activity_id"]),
        award_id=int(row["award_id"]),
        prize_id=int(row["prize_id"]),
        award_name=str(row["award_name"]),
        prize_name=str(row["prize_name"]),
        draw_number=int(row["draw_number"]),
        remaining_quantity=int(row["remaining_quantity"]),
        prize_image_url=prize_image_url(str(row["activity_id"]), int(row["prize_id"]), row["image_id"]),
        winner={
            "activity_user_id": int(row["activity_user_id"]),
            "username": str(row["username"]),
        },
        drawn_at=datetime.fromisoformat(str(row["drawn_at"])),
    )
