from datetime import datetime, timezone
import sqlite3

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from app.core.config import Settings, get_settings
from app.core.database import transaction
from app.core.security import create_access_token, decode_access_token_payload
from app.modules.activities.router import ActivityPublicResponse, get_activity


router = APIRouter(prefix="/activities", tags=["activity-auth"])
bearer = HTTPBearer(auto_error=False)


class ActivityCredentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=5, max_length=30)

    @field_validator("username", "phone")
    @classmethod
    def strip_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("用户名和手机号不能为空")
        return value


class ActivityUserResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    activity_id: str
    username: str


@router.get("/{activity_id}", response_model=ActivityPublicResponse)
def get_public_activity(activity_id: str, settings: Settings = Depends(get_settings)) -> ActivityPublicResponse:
    activity = get_activity(activity_id, settings)
    return ActivityPublicResponse(
        activity_id=activity.activity_id,
        name=activity.name,
        description=activity.description,
        status=activity.status,
    )


def require_activity_user(
    activity_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录活动")
    try:
        payload = decode_access_token_payload(credentials.credentials, settings)
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="活动登录已失效") from error
    if payload.get("activity_id") != activity_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能访问其他活动")
    username = str(payload["sub"])
    with transaction(settings) as connection:
        user = connection.execute(
            "SELECT id FROM activity_users WHERE activity_id = ? AND username = ?",
            (activity_id, username),
        ).fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="活动用户不存在")
    return username


def make_user_response(activity_id: str, username: str, settings: Settings) -> ActivityUserResponse:
    return ActivityUserResponse(
        access_token=create_access_token(username, settings, activity_id=activity_id),
        activity_id=activity_id,
        username=username,
    )


@router.post("/{activity_id}/auth/register", response_model=ActivityUserResponse, status_code=status.HTTP_201_CREATED)
def register_activity_user(
    activity_id: str,
    payload: ActivityCredentials,
    settings: Settings = Depends(get_settings),
) -> ActivityUserResponse:
    get_activity(activity_id, settings)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with transaction(settings) as connection:
            connection.execute(
                "INSERT INTO activity_users(activity_id, username, phone, created_at) VALUES (?, ?, ?, ?)",
                (activity_id, payload.username, payload.phone, now),
            )
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该活动手机号已注册") from error
    return make_user_response(activity_id, payload.username, settings)


@router.post("/{activity_id}/auth/login", response_model=ActivityUserResponse)
def login_activity_user(
    activity_id: str,
    payload: ActivityCredentials,
    settings: Settings = Depends(get_settings),
) -> ActivityUserResponse:
    get_activity(activity_id, settings)
    with transaction(settings) as connection:
        user = connection.execute(
            "SELECT username FROM activity_users WHERE activity_id = ? AND username = ? AND phone = ?",
            (activity_id, payload.username, payload.phone),
        ).fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或手机号不匹配")
    return make_user_response(activity_id, payload.username, settings)


@router.get("/{activity_id}/me", response_model=ActivityUserResponse)
def get_activity_user(
    activity_id: str,
    username: str = Depends(require_activity_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> ActivityUserResponse:
    return ActivityUserResponse(
        access_token=credentials.credentials,
        activity_id=activity_id,
        username=username,
    )
