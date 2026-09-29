from collections.abc import Collection
from datetime import datetime
import hmac
import secrets
import sqlite3

from app.core.config import Settings
from app.core.database import transaction
from app.modules.participants.avatar import AVATAR_COUNT, AvatarAssignmentError, validate_avatar_id
from .media_service import cleanup_lottery_media_keys, scan_lottery_media
from .models import (
    LotteryConfigError,
    LotteryConfigResponse,
    LotteryConfigUpdate,
    LotteryEntryPage,
    LotteryEntryStatus,
    LotteryEntryUpdate,
    LotteryEntryUpdateResponse,
    LotteryDrawAdmin,
    LotteryDrawError,
    LotteryDrawOutcome,
    LotteryHistoryPage,
    LotteryRoundParticipant,
)
from .round_state import LotteryRound
from .repository import (
    activity_or_raise,
    admin_draw,
    config_response,
    draw_count,
    draw_row,
    entry_where,
    ensure_config,
    lottery_entry,
    lottery_entry_row,
    lottery_entry_rows,
    lottery_entry_summary,
    now,
    prize_or_raise,
    public_draw,
)
from .snapshot import get_lottery_snapshot, public_config, public_snapshot, reset_lottery


def get_lottery_config(activity_id: str, settings: Settings) -> LotteryConfigResponse:
    with transaction(settings) as connection:
        return config_response(connection, activity_id)


def get_lottery_entries(
    activity_id: str,
    prize_id: int,
    settings: Settings,
    *,
    keyword: str | None,
    status: LotteryEntryStatus,
    page: int,
    page_size: int,
) -> LotteryEntryPage:
    normalized_keyword = keyword.strip() if keyword else None
    with transaction(settings) as connection:
        config = ensure_config(connection, activity_id)
        prize_or_raise(connection, activity_id, prize_id)
        rows, total = lottery_entry_rows(
            connection,
            activity_id,
            prize_id,
            status=status,
            keyword=normalized_keyword or None,
            no_repeat=bool(config["no_repeat_across_prizes"]),
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return LotteryEntryPage(
            prize_id=prize_id,
            items=[lottery_entry(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
            has_more=page * page_size < total,
            summary=lottery_entry_summary(
                connection,
                activity_id,
                prize_id,
                no_repeat=bool(config["no_repeat_across_prizes"]),
            ),
        )


def verify_lottery_security_code(activity_id: str, security_code: str, settings: Settings) -> None:
    with transaction(settings) as connection:
        activity_or_raise(connection, activity_id)

    configured_code = settings.lottery_security_code
    if not configured_code.strip():
        raise LotteryConfigError(
            "security_code_not_configured",
            "抽奖安全码尚未配置，请先在后端配置文件中设置 LOTTERY_SECURITY_CODE",
        )
    if not hmac.compare_digest(
        security_code.encode("utf-8"),
        configured_code.encode("utf-8"),
    ):
        raise LotteryConfigError("security_code_invalid", "安全码错误")


def update_lottery_entry(
    activity_id: str,
    prize_id: int,
    activity_user_id: int,
    payload: LotteryEntryUpdate,
    settings: Settings,
) -> LotteryEntryUpdateResponse:
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        config = ensure_config(connection, activity_id)
        prize_or_raise(connection, activity_id, prize_id)
        lottery_entry_row(connection, activity_id, prize_id, activity_user_id)
        current_time = now()
        connection.execute(
            """INSERT INTO lottery_prize_entries(
                   activity_id, prize_id, activity_user_id, is_blacklisted, is_whitelisted, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(activity_id, prize_id, activity_user_id) DO UPDATE SET
                   is_blacklisted = excluded.is_blacklisted,
                   is_whitelisted = excluded.is_whitelisted,
                   updated_at = excluded.updated_at""",
            (
                activity_id,
                prize_id,
                activity_user_id,
                int(payload.is_blacklisted),
                int(payload.is_whitelisted),
                current_time,
                current_time,
            ),
        )
        return LotteryEntryUpdateResponse(
            prize_id=prize_id,
            entry=lottery_entry(lottery_entry_row(connection, activity_id, prize_id, activity_user_id)),
            summary=lottery_entry_summary(
                connection,
                activity_id,
                prize_id,
                no_repeat=bool(config["no_repeat_across_prizes"]),
            ),
        )


def _replace_awards(connection: sqlite3.Connection, activity_id: str, payload: LotteryConfigUpdate) -> None:
    if payload.awards is None:
        return
    kept_ids: list[int] = []
    for award in payload.awards:
        if award.award_id:
            existing = connection.execute(
                "SELECT award_id FROM lottery_awards WHERE activity_id = ? AND award_id = ?",
                (activity_id, award.award_id),
            ).fetchone()
            if not existing:
                raise LotteryConfigError("invalid_award", "奖项不属于当前活动")
            award_id = int(award.award_id)
            connection.execute(
                "UPDATE lottery_awards SET name = ?, sort_order = ? "
                "WHERE activity_id = ? AND award_id = ?",
                (award.name, award.sort_order, activity_id, award_id),
            )
        else:
            cursor = connection.execute(
                "INSERT INTO lottery_awards(activity_id, name, sort_order) VALUES (?, ?, ?)",
                (activity_id, award.name, award.sort_order),
            )
            award_id = int(cursor.lastrowid)
        kept_ids.append(award_id)
    old_awards = connection.execute(
        "SELECT award_id FROM lottery_awards WHERE activity_id = ?", (activity_id,)
    ).fetchall()
    for old_award in old_awards:
        if int(old_award["award_id"]) not in kept_ids:
            connection.execute(
                "DELETE FROM lottery_awards WHERE activity_id = ? AND award_id = ?",
                (activity_id, int(old_award["award_id"])),
            )


def _replace_prizes(
    connection: sqlite3.Connection, activity_id: str, payload: LotteryConfigUpdate
) -> set[str]:
    if payload.prizes is None:
        return set()
    award_ids = {
        int(row["award_id"])
        for row in connection.execute(
            "SELECT award_id FROM lottery_awards WHERE activity_id = ?", (activity_id,)
        ).fetchall()
    }
    kept_ids: list[int] = []
    for prize in payload.prizes:
        if prize.award_id not in award_ids:
            raise LotteryConfigError("invalid_award", "奖品关联的奖项不属于当前活动")
        if prize.prize_id:
            existing = connection.execute(
                "SELECT prize_id FROM lottery_prizes WHERE activity_id = ? AND prize_id = ?",
                (activity_id, prize.prize_id),
            ).fetchone()
            if not existing:
                raise LotteryConfigError("invalid_prize", "奖品不属于当前活动")
            if draw_count(connection, activity_id, prize.prize_id) > prize.quantity:
                raise LotteryConfigError("quantity_below_draws", "奖品数量不能少于已有中奖记录")
            connection.execute(
                "UPDATE lottery_prizes SET award_id = ?, name = ?, quantity = ?, sort_order = ?, "
                "is_enabled = ? WHERE activity_id = ? AND prize_id = ?",
                (
                    prize.award_id,
                    prize.name,
                    prize.quantity,
                    prize.sort_order,
                    int(prize.is_enabled),
                    activity_id,
                    prize.prize_id,
                ),
            )
            prize_id = int(prize.prize_id)
        else:
            cursor = connection.execute(
                "INSERT INTO lottery_prizes(activity_id, award_id, name, quantity, sort_order, is_enabled) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    activity_id,
                    prize.award_id,
                    prize.name,
                    prize.quantity,
                    prize.sort_order,
                    int(prize.is_enabled),
                ),
            )
            prize_id = int(cursor.lastrowid)
        kept_ids.append(prize_id)
    old_prizes = connection.execute(
        "SELECT prize_id, image_storage_key FROM lottery_prizes WHERE activity_id = ?", (activity_id,)
    ).fetchall()
    deleted_storage_keys: set[str] = set()
    for old_prize in old_prizes:
        old_id = int(old_prize["prize_id"])
        if old_id not in kept_ids:
            if draw_count(connection, activity_id, old_id):
                raise LotteryConfigError("prize_has_draws", "已有中奖记录的奖品不能删除")
            connection.execute(
                "DELETE FROM lottery_prizes WHERE activity_id = ? AND prize_id = ?",
                (activity_id, old_id),
            )
            if old_prize["image_storage_key"]:
                deleted_storage_keys.add(str(old_prize["image_storage_key"]))
    return deleted_storage_keys


def update_lottery_config(
    activity_id: str,
    payload: LotteryConfigUpdate,
    settings: Settings,
) -> LotteryConfigResponse:
    try:
        with transaction(settings) as connection:
            connection.execute("BEGIN IMMEDIATE")
            config = ensure_config(connection, activity_id)
            before_storage_keys = {
                str(row["image_storage_key"])
                for row in connection.execute(
                    "SELECT image_storage_key FROM lottery_prizes "
                    "WHERE activity_id = ? AND image_storage_key IS NOT NULL",
                    (activity_id,),
                ).fetchall()
            }
            current_time = now()
            connection.execute(
                "UPDATE lottery_configs SET no_repeat_across_prizes = ?, rolling_name_count = ?, updated_at = ? "
                "WHERE activity_id = ?",
                (
                    int(
                        payload.no_repeat_across_prizes
                        if payload.no_repeat_across_prizes is not None
                        else bool(config["no_repeat_across_prizes"])
                    ),
                    payload.rolling_name_count
                    if payload.rolling_name_count is not None
                    else int(config["rolling_name_count"]),
                    current_time,
                    activity_id,
                ),
            )
            _replace_awards(connection, activity_id, payload)
            _replace_prizes(connection, activity_id, payload)
            response = config_response(connection, activity_id)
            after_storage_keys = {
                str(row["image_storage_key"])
                for row in connection.execute(
                    "SELECT image_storage_key FROM lottery_prizes "
                    "WHERE activity_id = ? AND image_storage_key IS NOT NULL",
                    (activity_id,),
                ).fetchall()
            }
            deleted_storage_keys = before_storage_keys - after_storage_keys
        if deleted_storage_keys:
            cleanup_lottery_media_keys(settings, deleted_storage_keys)
        scan_lottery_media(settings, grace_seconds=300)
        return response
    except sqlite3.IntegrityError as error:
        raise LotteryConfigError("config_conflict", "抽奖配置与已有记录冲突") from error


def _eligible_candidates(
    connection: sqlite3.Connection,
    activity_id: str,
    prize_id: int,
    *,
    no_repeat: bool,
) -> list[sqlite3.Row]:
    where, parameters = entry_where(
        connection,
        activity_id,
        prize_id,
        status="eligible",
        keyword=None,
        no_repeat=no_repeat,
    )
    return connection.execute(
        """SELECT u.id, u.username, u.phone, u.created_at
             FROM activity_users u
             LEFT JOIN lottery_prize_entries e
               ON e.activity_id = u.activity_id AND e.prize_id = ? AND e.activity_user_id = u.id
            WHERE """ + where + " ORDER BY u.id",
        (prize_id, *parameters),
    ).fetchall()


def _ensure_mobile_lottery_permission(
    connection: sqlite3.Connection,
    activity_id: str,
    activity_user_id: int,
) -> None:
    row = connection.execute(
        "SELECT is_active, can_mobile_lottery FROM activity_users "
        "WHERE activity_id = ? AND id = ?",
        (activity_id, activity_user_id),
    ).fetchone()
    if not row or not bool(row["is_active"]) or not bool(row["can_mobile_lottery"]):
        raise LotteryDrawError("mobile_lottery_forbidden", "你没有移动端抽奖权限")


def _draw_prize_row(
    connection: sqlite3.Connection,
    activity_id: str,
    prize_id: int,
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT p.prize_id, p.award_id, a.name AS award_name, p.name, p.quantity, p.is_enabled "
        "FROM lottery_prizes p JOIN lottery_awards a ON a.award_id = p.award_id "
        "AND a.activity_id = p.activity_id WHERE p.activity_id = ? AND p.prize_id = ?",
        (activity_id, prize_id),
    ).fetchone()


def validate_lottery_prize_selection(
    activity_id: str,
    prize_id: int,
    settings: Settings,
    *,
    mobile_activity_user_id: int | None = None,
) -> None:
    with transaction(settings) as connection:
        activity_or_raise(connection, activity_id)
        if mobile_activity_user_id is not None:
            _ensure_mobile_lottery_permission(connection, activity_id, mobile_activity_user_id)
        prize = _draw_prize_row(connection, activity_id, prize_id)
        if not prize:
            raise LotteryDrawError("invalid_prize", "奖品不存在或不属于当前活动")
        if not bool(prize["is_enabled"]):
            raise LotteryDrawError("prize_disabled", "该奖品已停用")
        if draw_count(connection, activity_id, prize_id) >= int(prize["quantity"]):
            raise LotteryDrawError("inventory_exhausted", "奖品库存不足")


def _round_avatar_id(activity_user_id: int, value: object) -> int:
    try:
        return validate_avatar_id(value)
    except AvatarAssignmentError:
        return (activity_user_id - 1) % AVATAR_COUNT + 1


def prepare_lottery_round(
    activity_id: str,
    prize_id: int,
    round_id: str,
    settings: Settings,
    *,
    mobile_activity_user_id: int | None = None,
) -> LotteryRound:
    round_id = round_id.strip()
    if not round_id or len(round_id) > 100:
        raise LotteryDrawError("invalid_request", "round_id 必须是 1 至 100 个字符")
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        if mobile_activity_user_id is not None:
            _ensure_mobile_lottery_permission(connection, activity_id, mobile_activity_user_id)
        activity = activity_or_raise(connection, activity_id)
        if activity["status"] != "open":
            raise LotteryDrawError("activity_not_started", "活动尚未开始或已经结束")
        config = ensure_config(connection, activity_id)
        prize = _draw_prize_row(connection, activity_id, prize_id)
        if not prize:
            raise LotteryDrawError("invalid_prize", "奖品不存在或不属于当前活动")
        if not bool(prize["is_enabled"]):
            raise LotteryDrawError("prize_disabled", "该奖品已停用")
        if draw_count(connection, activity_id, prize_id) >= int(prize["quantity"]):
            raise LotteryDrawError("inventory_exhausted", "该奖品库存不足")
        candidates = _eligible_candidates(
            connection,
            activity_id,
            prize_id,
            no_repeat=bool(config["no_repeat_across_prizes"]),
        )
        if not candidates:
            raise LotteryDrawError("no_eligible_winner", "当前没有可中奖的用户")
        participant_rows = connection.execute(
            "SELECT id, username, avatar_id FROM activity_users "
            "WHERE activity_id = ? ORDER BY id",
            (activity_id,),
        ).fetchall()
        participants = tuple(
            LotteryRoundParticipant(
                activity_user_id=int(row["id"]),
                username=str(row["username"]),
                avatar_id=_round_avatar_id(int(row["id"]), row["avatar_id"]),
            )
            for row in participant_rows
        )
        started_at = datetime.fromisoformat(now())
        return LotteryRound(
            activity_id=activity_id,
            round_id=round_id,
            award_id=int(prize["award_id"]),
            award_name=str(prize["award_name"]),
            prize_id=int(prize["prize_id"]),
            prize_name=str(prize["name"]),
            participants=participants,
            candidate_user_ids=frozenset(int(row["id"]) for row in candidates),
            started_at=started_at,
        )


def draw_lottery(
    activity_id: str,
    prize_id: int,
    request_id: str,
    settings: Settings,
    *,
    candidate_user_ids: Collection[int] | None = None,
    existing_only: bool = False,
    mobile_activity_user_id: int | None = None,
) -> LotteryDrawOutcome:
    request_id = request_id.strip()
    if not request_id or len(request_id) > 100:
        raise LotteryDrawError("invalid_request", "request_id 必须是 1 至 100 个字符")
    with transaction(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        if mobile_activity_user_id is not None:
            _ensure_mobile_lottery_permission(connection, activity_id, mobile_activity_user_id)
        existing = connection.execute(
            "SELECT draw_id FROM lottery_draws WHERE activity_id = ? AND request_id = ?",
            (activity_id, request_id),
        ).fetchone()
        if existing:
            row = draw_row(connection, int(existing["draw_id"]))
            if int(row["prize_id"]) != prize_id:
                raise LotteryDrawError("request_conflict", "request_id 已用于其他奖品")
            return LotteryDrawOutcome(admin_draw(row), public_draw(row), [], True)
        if existing_only:
            raise LotteryDrawError("round_not_found", "抽奖轮次不存在或已过期")
        activity = activity_or_raise(connection, activity_id)
        if activity["status"] != "open":
            raise LotteryDrawError("activity_not_started", "活动尚未开始或已经结束")
        config = ensure_config(connection, activity_id)
        prize = _draw_prize_row(connection, activity_id, prize_id)
        if not prize:
            raise LotteryDrawError("invalid_prize", "奖品不存在或不属于当前活动")
        if not bool(prize["is_enabled"]):
            raise LotteryDrawError("prize_disabled", "该奖品已停用")
        drawn_count = draw_count(connection, activity_id, prize_id)
        if drawn_count >= int(prize["quantity"]):
            raise LotteryDrawError("inventory_exhausted", "该奖品库存不足")
        candidates = _eligible_candidates(
            connection,
            activity_id,
            prize_id,
            no_repeat=bool(config["no_repeat_across_prizes"]),
        )
        if candidate_user_ids is not None:
            frozen_ids = {int(user_id) for user_id in candidate_user_ids}
            candidates = [candidate for candidate in candidates if int(candidate["id"]) in frozen_ids]
        if not candidates:
            raise LotteryDrawError("no_eligible_winner", "当前没有可中奖的用户")
        winner = secrets.choice(candidates)
        current_time = now()
        cursor = connection.execute(
            "INSERT INTO lottery_draws(activity_id, award_id, prize_id, activity_user_id, draw_number, "
            "request_id, drawn_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                activity_id,
                int(prize["award_id"]),
                prize_id,
                int(winner["id"]),
                drawn_count + 1,
                request_id,
                current_time,
            ),
        )
        row = draw_row(connection, int(cursor.lastrowid))
        roll_count = int(config["rolling_name_count"])
        other_names = [
            str(candidate["username"])
            for candidate in candidates
            if candidate["id"] != winner["id"]
        ]
        if len(other_names) > max(0, roll_count - 1):
            other_names = secrets.SystemRandom().sample(other_names, roll_count - 1)
        roll_names = other_names + [str(winner["username"])]
        return LotteryDrawOutcome(admin_draw(row), public_draw(row), roll_names, False)


def list_lottery_history(
    activity_id: str,
    settings: Settings,
    *,
    limit: int = 100,
    before_id: int | None = None,
) -> LotteryHistoryPage:
    with transaction(settings) as connection:
        activity_or_raise(connection, activity_id)
        if before_id is None:
            rows = connection.execute(
                "SELECT draw_id FROM lottery_draws WHERE activity_id = ? "
                "ORDER BY draw_id DESC LIMIT ?",
                (activity_id, limit + 1),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT draw_id FROM lottery_draws WHERE activity_id = ? AND draw_id < ? "
                "ORDER BY draw_id DESC LIMIT ?",
                (activity_id, before_id, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        draws = [admin_draw(draw_row(connection, int(row["draw_id"]))) for row in rows[:limit]]
    return LotteryHistoryPage(items=draws, has_more=has_more)
