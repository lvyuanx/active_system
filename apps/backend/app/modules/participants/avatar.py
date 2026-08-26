import secrets
import sqlite3


AVATAR_ID_MIN = 1
AVATAR_ID_MAX = 20
AVATAR_COUNT = AVATAR_ID_MAX - AVATAR_ID_MIN + 1


class AvatarAssignmentError(RuntimeError):
    """头像数据不存在、越界或无法在当前活动用户上安全分配。"""


def random_avatar_id() -> int:
    return secrets.randbelow(AVATAR_COUNT) + AVATAR_ID_MIN


def validate_avatar_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not AVATAR_ID_MIN <= value <= AVATAR_ID_MAX:
        raise AvatarAssignmentError("活动用户头像数据无效")
    return value


def ensure_avatar_id(
    connection: sqlite3.Connection,
    activity_id: str,
    activity_user_id: int,
    current_avatar_id: object | None,
) -> int:
    if current_avatar_id is not None:
        return validate_avatar_id(current_avatar_id)

    avatar_id = random_avatar_id()
    result = connection.execute(
        "UPDATE activity_users SET avatar_id = ? "
        "WHERE activity_id = ? AND id = ? AND avatar_id IS NULL",
        (avatar_id, activity_id, activity_user_id),
    )
    if result.rowcount == 1:
        return avatar_id
    # A concurrent request may have won the conditional update; keep its value.
    row = connection.execute(
        "SELECT avatar_id FROM activity_users WHERE activity_id = ? AND id = ?",
        (activity_id, activity_user_id),
    ).fetchone()
    if not row or row["avatar_id"] is None:
        raise AvatarAssignmentError("活动用户头像分配失败")
    return validate_avatar_id(row["avatar_id"])
