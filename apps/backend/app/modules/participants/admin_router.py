from datetime import datetime
from enum import Enum
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.database import transaction
from app.modules.activities.router import get_activity
from app.modules.auth import require_superuser


admin_router = APIRouter(prefix="/admin/activities", tags=["participants-admin"])


class ParticipantAction(str, Enum):
    MUTE = "mute"
    UNMUTE = "unmute"
    DEACTIVATE = "deactivate"
    ACTIVATE = "activate"
    GRANT_MOBILE_LOTTERY = "mobile-lottery/grant"
    REVOKE_MOBILE_LOTTERY = "mobile-lottery/revoke"


class ActivityParticipantResponse(BaseModel):
    activity_id: str
    activity_user_id: int
    username: str
    phone: str
    joined_at: datetime
    is_active: bool
    is_muted: bool
    can_mobile_lottery: bool


class ActivityParticipantPage(BaseModel):
    items: list[ActivityParticipantResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    has_more: bool


def _participant_from_row(row: sqlite3.Row) -> ActivityParticipantResponse:
    return ActivityParticipantResponse(
        activity_id=str(row["activity_id"]),
        activity_user_id=int(row["id"]),
        username=str(row["username"]),
        phone=str(row["phone"]),
        joined_at=datetime.fromisoformat(str(row["created_at"])),
        is_active=bool(row["is_active"]),
        is_muted=bool(row["is_muted"]),
        can_mobile_lottery=bool(row["can_mobile_lottery"]),
    )


def _change_participant(
    activity_id: str,
    activity_user_id: int,
    action: ParticipantAction,
    settings: Settings,
) -> ActivityParticipantResponse:
    get_activity(activity_id, settings)
    with transaction(settings) as connection:
        row = connection.execute(
            "SELECT id, activity_id, username, phone, created_at, is_active, is_muted, can_mobile_lottery "
            "FROM activity_users WHERE activity_id = ? AND id = ?",
            (activity_id, activity_user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动用户不存在")

        if action == ParticipantAction.MUTE:
            connection.execute(
                "UPDATE activity_users SET is_muted = 1 WHERE activity_id = ? AND id = ?",
                (activity_id, activity_user_id),
            )
        elif action == ParticipantAction.UNMUTE:
            connection.execute(
                "UPDATE activity_users SET is_muted = 0 WHERE activity_id = ? AND id = ?",
                (activity_id, activity_user_id),
            )
        elif action == ParticipantAction.DEACTIVATE:
            connection.execute(
                "UPDATE activity_users SET is_active = 0, session_version = session_version + 1 "
                "WHERE activity_id = ? AND id = ? AND is_active = 1",
                (activity_id, activity_user_id),
            )
        elif action == ParticipantAction.GRANT_MOBILE_LOTTERY:
            connection.execute(
                "UPDATE activity_users SET can_mobile_lottery = 1 WHERE activity_id = ? AND id = ?",
                (activity_id, activity_user_id),
            )
        elif action == ParticipantAction.REVOKE_MOBILE_LOTTERY:
            connection.execute(
                "UPDATE activity_users SET can_mobile_lottery = 0 WHERE activity_id = ? AND id = ?",
                (activity_id, activity_user_id),
            )
        else:
            connection.execute(
                "UPDATE activity_users SET is_active = 1 WHERE activity_id = ? AND id = ?",
                (activity_id, activity_user_id),
            )

        updated = connection.execute(
            "SELECT id, activity_id, username, phone, created_at, is_active, is_muted, can_mobile_lottery "
            "FROM activity_users WHERE activity_id = ? AND id = ?",
            (activity_id, activity_user_id),
        ).fetchone()
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="活动用户更新失败")
    return _participant_from_row(updated)


@admin_router.get("/{activity_id}/participants", response_model=ActivityParticipantPage)
def list_participants(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ActivityParticipantPage:
    get_activity(activity_id, settings)
    normalized_keyword = keyword.strip() if keyword else ""
    clauses = ["activity_id = ?"]
    parameters: list[object] = [activity_id]
    if normalized_keyword:
        clauses.append("(username LIKE ? OR phone LIKE ?)")
        pattern = f"%{normalized_keyword}%"
        parameters.extend([pattern, pattern])
    where_clause = " AND ".join(clauses)
    with transaction(settings) as connection:
        count_row = connection.execute(
            f"SELECT COUNT(*) AS total FROM activity_users WHERE {where_clause}",
            parameters,
        ).fetchone()
        rows = connection.execute(
            f"SELECT id, activity_id, username, phone, created_at, is_active, is_muted, can_mobile_lottery "
            f"FROM activity_users WHERE {where_clause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (*parameters, page_size, (page - 1) * page_size),
        ).fetchall()
    total = int(count_row["total"])
    return ActivityParticipantPage(
        items=[_participant_from_row(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        has_more=page * page_size < total,
    )


@admin_router.post(
    "/{activity_id}/participants/{activity_user_id}/mute",
    response_model=ActivityParticipantResponse,
)
def mute_participant(
    activity_id: str,
    activity_user_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityParticipantResponse:
    return _change_participant(activity_id, activity_user_id, ParticipantAction.MUTE, settings)


@admin_router.post(
    "/{activity_id}/participants/{activity_user_id}/unmute",
    response_model=ActivityParticipantResponse,
)
def unmute_participant(
    activity_id: str,
    activity_user_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityParticipantResponse:
    return _change_participant(activity_id, activity_user_id, ParticipantAction.UNMUTE, settings)


@admin_router.post(
    "/{activity_id}/participants/{activity_user_id}/deactivate",
    response_model=ActivityParticipantResponse,
)
def deactivate_participant(
    activity_id: str,
    activity_user_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityParticipantResponse:
    return _change_participant(activity_id, activity_user_id, ParticipantAction.DEACTIVATE, settings)


@admin_router.post(
    "/{activity_id}/participants/{activity_user_id}/activate",
    response_model=ActivityParticipantResponse,
)
def activate_participant(
    activity_id: str,
    activity_user_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityParticipantResponse:
    return _change_participant(activity_id, activity_user_id, ParticipantAction.ACTIVATE, settings)


@admin_router.post(
    "/{activity_id}/participants/{activity_user_id}/mobile-lottery/grant",
    response_model=ActivityParticipantResponse,
)
def grant_mobile_lottery(
    activity_id: str,
    activity_user_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityParticipantResponse:
    return _change_participant(
        activity_id,
        activity_user_id,
        ParticipantAction.GRANT_MOBILE_LOTTERY,
        settings,
    )


@admin_router.post(
    "/{activity_id}/participants/{activity_user_id}/mobile-lottery/revoke",
    response_model=ActivityParticipantResponse,
)
def revoke_mobile_lottery(
    activity_id: str,
    activity_user_id: int,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityParticipantResponse:
    return _change_participant(
        activity_id,
        activity_user_id,
        ParticipantAction.REVOKE_MOBILE_LOTTERY,
        settings,
    )
