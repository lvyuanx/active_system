from dataclasses import dataclass
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
from app.modules.participants.avatar import (
    AVATAR_ID_MAX,
    AVATAR_ID_MIN,
    AvatarAssignmentError,
    ensure_avatar_id,
    random_avatar_id,
)
from app.modules.sms.service import (
    SmsConfigurationError,
    SmsProviderError,
    check_sms_code,
    normalize_phone,
    normalize_sms_code,
)


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
    activity_user_id: int
    username: str
    joined_at: datetime
    avatar_id: int = Field(ge=AVATAR_ID_MIN, le=AVATAR_ID_MAX)
    can_mobile_lottery: bool = False


class SmsLoginRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11)
    code: str = Field(min_length=4, max_length=8)
    username: str | None = Field(default=None, max_length=100)

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value: object) -> str:
        return normalize_phone(value)

    @field_validator("code", mode="before")
    @classmethod
    def validate_code(cls, value: object) -> str:
        return normalize_sms_code(value)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("姓名必须是文本")
        return value.strip() or None


class SmsLoginResponse(BaseModel):
    needs_name: bool = False
    user: ActivityUserResponse | None = None


@dataclass(frozen=True)
class ActivityPrincipal:
    activity_id: str
    activity_user_id: int
    username: str
    joined_at: datetime
    can_mobile_lottery: bool


def _token_session_version(payload: dict[str, object]) -> int | None:
    if "activity_user_session_version" not in payload:
        return None
    value = payload["activity_user_session_version"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请重新登录活动")
    return value


def _session_version_matches(payload: dict[str, object], database_version: int) -> bool:
    token_version = _token_session_version(payload)
    return token_version == database_version if token_version is not None else database_version == 0


@router.get("/{activity_id}", response_model=ActivityPublicResponse)
def get_public_activity(activity_id: str, settings: Settings = Depends(get_settings)) -> ActivityPublicResponse:
    activity = get_activity(activity_id, settings)
    return ActivityPublicResponse(
        activity_id=activity.activity_id,
        name=activity.name,
        description=activity.description,
        status=activity.status,
    )


def get_activity_principal(
    activity_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> ActivityPrincipal:
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
        user = None
        if "activity_user_id" in payload:
            activity_user_id = payload["activity_user_id"]
            if isinstance(activity_user_id, bool) or not isinstance(activity_user_id, int):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请重新登录活动")
            user = connection.execute(
                "SELECT id, username, created_at, is_active, session_version, can_mobile_lottery "
                "FROM activity_users "
                "WHERE activity_id = ? AND id = ?",
                (activity_id, activity_user_id),
            ).fetchone()
            if user and user["username"] != username:
                user = None
        else:
            # Old tokens did not contain the stable ID. They remain valid only when
            # the username identifies exactly one participant in this activity.
            matches = connection.execute(
                "SELECT id, username, created_at, is_active, session_version, can_mobile_lottery "
                "FROM activity_users "
                "WHERE activity_id = ? AND username = ? ORDER BY id",
                (activity_id, username),
            ).fetchall()
            user = matches[0] if len(matches) == 1 else None
    if (
        not user
        or not bool(user["is_active"])
        or not _session_version_matches(payload, int(user["session_version"]))
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请重新登录活动")
    return ActivityPrincipal(
        activity_id=activity_id,
        activity_user_id=int(user["id"]),
        username=str(user["username"]),
        joined_at=datetime.fromisoformat(str(user["created_at"])),
        can_mobile_lottery=bool(user["can_mobile_lottery"]),
    )


def require_activity_user(
    activity_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    return get_activity_principal(activity_id, credentials, settings).username


def make_user_response(
    activity_id: str,
    username: str,
    settings: Settings,
    *,
    activity_user_id: int | None = None,
    access_token: str | None = None,
) -> ActivityUserResponse:
    with transaction(settings) as connection:
        if activity_user_id is None:
            row = connection.execute(
                "SELECT id, username, created_at, avatar_id, session_version, can_mobile_lottery "
                "FROM activity_users "
                "WHERE activity_id = ? AND username = ? ORDER BY id DESC LIMIT 1",
                (activity_id, username),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT id, username, created_at, avatar_id, session_version, can_mobile_lottery "
                "FROM activity_users "
                "WHERE activity_id = ? AND id = ?",
                (activity_id, activity_user_id),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="活动用户不存在")
        try:
            avatar_id = ensure_avatar_id(connection, activity_id, int(row["id"]), row["avatar_id"])
        except AvatarAssignmentError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="活动头像分配失败",
            ) from error
        return ActivityUserResponse(
            access_token=access_token
            or create_access_token(
                str(row["username"]),
                settings,
                activity_id=activity_id,
                activity_user_id=int(row["id"]),
                activity_user_session_version=int(row["session_version"]),
            ),
            activity_id=activity_id,
            activity_user_id=int(row["id"]),
            username=str(row["username"]),
            joined_at=datetime.fromisoformat(str(row["created_at"])),
            avatar_id=avatar_id,
            can_mobile_lottery=bool(row["can_mobile_lottery"]),
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
            avatar_id = random_avatar_id()
            cursor = connection.execute(
                "INSERT INTO activity_users(activity_id, username, phone, created_at, avatar_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (activity_id, payload.username, payload.phone, now, avatar_id),
            )
            row = connection.execute(
                "SELECT id, username, created_at, avatar_id, session_version, can_mobile_lottery "
                "FROM activity_users "
                "WHERE activity_id = ? AND id = ?",
                (activity_id, cursor.lastrowid),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="活动用户创建失败")
            return ActivityUserResponse(
                access_token=create_access_token(
                    str(row["username"]),
                    settings,
                    activity_id=activity_id,
                    activity_user_id=int(row["id"]),
                    activity_user_session_version=int(row["session_version"]),
                ),
                activity_id=activity_id,
                activity_user_id=int(row["id"]),
                username=str(row["username"]),
                joined_at=datetime.fromisoformat(str(row["created_at"])),
                avatar_id=int(row["avatar_id"]),
                can_mobile_lottery=bool(row["can_mobile_lottery"]),
            )
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该活动手机号已注册") from error


@router.post("/{activity_id}/auth/login", response_model=ActivityUserResponse)
def login_activity_user(
    activity_id: str,
    payload: ActivityCredentials,
    settings: Settings = Depends(get_settings),
) -> ActivityUserResponse:
    get_activity(activity_id, settings)
    with transaction(settings) as connection:
        user = connection.execute(
            "SELECT id, username, is_active FROM activity_users "
            "WHERE activity_id = ? AND username = ? AND phone = ?",
            (activity_id, payload.username, payload.phone),
        ).fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或手机号不匹配")
    if not bool(user["is_active"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该活动用户已停用")
    return make_user_response(activity_id, payload.username, settings, activity_user_id=int(user["id"]))


@router.post("/{activity_id}/auth/sms-login", response_model=SmsLoginResponse)
def sms_login_activity_user(
    activity_id: str,
    payload: SmsLoginRequest,
    settings: Settings = Depends(get_settings),
) -> SmsLoginResponse:
    get_activity(activity_id, settings)
    try:
        verified = check_sms_code(payload.phone, payload.code, settings)
    except SmsConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="短信服务未配置",
        ) from error
    except SmsProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="短信核验失败，请稍后重试",
        ) from error
    if not verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="验证码错误或已失效")

    with transaction(settings) as connection:
        user = connection.execute(
            "SELECT id, username, is_active FROM activity_users "
            "WHERE activity_id = ? AND phone = ?",
            (activity_id, payload.phone),
        ).fetchone()
    if user:
        if not bool(user["is_active"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该活动用户已停用")
        return SmsLoginResponse(
            user=make_user_response(activity_id, str(user["username"]), settings, activity_user_id=int(user["id"]))
        )
    if not payload.username:
        return SmsLoginResponse(needs_name=True)

    created = register_activity_user(
        activity_id,
        ActivityCredentials(username=payload.username, phone=payload.phone),
        settings,
    )
    return SmsLoginResponse(user=created)


@router.get("/{activity_id}/me", response_model=ActivityUserResponse)
def get_activity_user(
    activity_id: str,
    principal: ActivityPrincipal = Depends(get_activity_principal),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> ActivityUserResponse:
    return make_user_response(
        activity_id,
        principal.username,
        settings,
        activity_user_id=principal.activity_user_id,
        access_token=credentials.credentials,
    )
