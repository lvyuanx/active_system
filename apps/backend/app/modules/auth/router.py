from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


def ensure_superuser(settings: Settings) -> None:
    init_database(settings)
    if not settings.superuser_password:
        return
    now = datetime.now(timezone.utc).isoformat()
    with transaction(settings) as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?", (settings.superuser_username,)
        ).fetchone()
        if existing:
            connection.execute(
                "UPDATE users SET password_hash = ?, is_superuser = 1 WHERE id = ?",
                (hash_password(settings.superuser_password), existing["id"]),
            )
        else:
            connection.execute(
                "INSERT INTO users(username, password_hash, is_superuser, created_at) VALUES (?, ?, 1, ?)",
                (settings.superuser_username, hash_password(settings.superuser_password), now),
            )


def require_superuser(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        username = decode_access_token(credentials.credentials, settings)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with transaction(settings) as connection:
        user = connection.execute(
            "SELECT is_superuser FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user["is_superuser"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有超级用户可以访问管理员功能")
    return username


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, settings: Settings = Depends(get_settings)) -> LoginResponse:
    ensure_superuser(settings)
    with transaction(settings) as connection:
        user = connection.execute(
            "SELECT username, password_hash, is_superuser FROM users WHERE username = ?",
            (payload.username,),
        ).fetchone()
    if not user or not user["is_superuser"] or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    return LoginResponse(access_token=create_access_token(user["username"], settings), username=user["username"])
