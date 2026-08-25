from datetime import datetime, timezone
from enum import Enum
import sqlite3
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from app.core.config import Settings, get_settings
from app.core.database import transaction
from app.modules.auth import require_superuser


router = APIRouter(prefix="/admin/activities", tags=["activities"])


class ActivityStatus(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    ENDED = "ended"


class ActivityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_times(self) -> "ActivityCreate":
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("活动名称不能为空")
        if self.description is not None:
            self.description = self.description.strip() or None
        if self.start_time and self.end_time:
            try:
                if self.end_time <= self.start_time:
                    raise ValueError("结束时间必须晚于开始时间")
            except TypeError as error:
                raise ValueError("开始时间和结束时间的时区格式必须一致") from error
        return self


class ActivityResponse(BaseModel):
    activity_id: str
    name: str
    description: str | None
    start_time: datetime | None
    end_time: datetime | None
    status: ActivityStatus
    created_at: datetime
    updated_at: datetime


class ActivityPublicResponse(BaseModel):
    activity_id: str
    name: str
    description: str | None
    status: ActivityStatus


def parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def row_to_activity(row: sqlite3.Row) -> ActivityResponse:
    return ActivityResponse(
        activity_id=row["activity_id"], name=row["name"], description=row["description"],
        start_time=parse_time(row["start_time"]), end_time=parse_time(row["end_time"]),
        status=row["status"],
        created_at=parse_time(row["created_at"]),
        updated_at=parse_time(row["updated_at"]),
    )


def get_activity(activity_id: str, settings: Settings) -> ActivityResponse:
    with transaction(settings) as connection:
        row = connection.execute("SELECT * FROM activities WHERE activity_id = ?", (activity_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
    return row_to_activity(row)


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity_detail(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityResponse:
    return get_activity(activity_id, settings)


@router.get("", response_model=list[ActivityResponse])
def list_activities(
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> list[ActivityResponse]:
    with transaction(settings) as connection:
        rows = connection.execute("SELECT * FROM activities ORDER BY created_at DESC").fetchall()
    return [row_to_activity(row) for row in rows]


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: ActivityCreate,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityResponse:
    now = datetime.now(timezone.utc).isoformat()
    activity_id = str(uuid4())
    with transaction(settings) as connection:
        connection.execute(
            """INSERT INTO activities(
                activity_id, name, description, start_time, end_time, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'closed', ?, ?)""",
            (
                activity_id,
                payload.name.strip(),
                payload.description,
                payload.start_time.isoformat() if payload.start_time else None,
                payload.end_time.isoformat() if payload.end_time else None,
                now,
                now,
            ),
        )
        row = connection.execute("SELECT * FROM activities WHERE activity_id = ?", (activity_id,)).fetchone()
    return row_to_activity(row)


def transition(activity_id: str, target: ActivityStatus, settings: Settings) -> ActivityResponse:
    now = datetime.now(timezone.utc).isoformat()
    with transaction(settings) as connection:
        row = connection.execute("SELECT * FROM activities WHERE activity_id = ?", (activity_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
        current = ActivityStatus(row["status"])
        allowed = (current == ActivityStatus.CLOSED and target == ActivityStatus.OPEN) or (
            current == ActivityStatus.OPEN and target == ActivityStatus.CLOSED
        ) or (current in (ActivityStatus.CLOSED, ActivityStatus.OPEN) and target == ActivityStatus.ENDED)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"活动当前状态为 {current.value}，不能执行该操作",
            )
        connection.execute(
            "UPDATE activities SET status = ?, updated_at = ? WHERE activity_id = ?",
            (target.value, now, activity_id),
        )
        updated = connection.execute("SELECT * FROM activities WHERE activity_id = ?", (activity_id,)).fetchone()
    return row_to_activity(updated)


@router.post("/{activity_id}/open", response_model=ActivityResponse)
def open_activity(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityResponse:
    return transition(activity_id, ActivityStatus.OPEN, settings)


@router.post("/{activity_id}/close", response_model=ActivityResponse)
def close_activity(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityResponse:
    return transition(activity_id, ActivityStatus.CLOSED, settings)


@router.post("/{activity_id}/end", response_model=ActivityResponse)
def end_activity(
    activity_id: str,
    _: str = Depends(require_superuser),
    settings: Settings = Depends(get_settings),
) -> ActivityResponse:
    return transition(activity_id, ActivityStatus.ENDED, settings)
