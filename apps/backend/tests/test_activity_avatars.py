from datetime import datetime, timedelta, timezone
import importlib
import sqlite3
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import init_database, transaction
from app.core.security import create_access_token
from app.main import app
from app.modules.participants.avatar import AVATAR_ID_MAX, AVATAR_ID_MIN, ensure_avatar_id


def make_client(
    tmp_path: Path,
    filename: str = "avatars.db",
    *,
    raise_server_exceptions: bool = True,
) -> tuple[TestClient, Settings]:
    settings = Settings(
        database_path=str(tmp_path / filename),
        jwt_secret="test-secret-at-least-thirty-two-bytes",
        superuser_username="root",
        superuser_password="secret-password",
    )
    init_database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app, raise_server_exceptions=raise_server_exceptions), settings


def create_activity(client: TestClient, name: str = "头像测试") -> str:
    login = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret-password"})
    response = client.post(
        "/api/v1/admin/activities",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()["activity_id"]


def read_avatar(settings: Settings, activity_id: str, activity_user_id: int) -> int | None:
    with transaction(settings) as connection:
        row = connection.execute(
            "SELECT avatar_id FROM activity_users WHERE activity_id = ? AND id = ?",
            (activity_id, activity_user_id),
        ).fetchone()
    return row["avatar_id"] if row else None


def set_avatar(settings: Settings, activity_id: str, activity_user_id: int, avatar_id: int | None) -> None:
    with transaction(settings) as connection:
        connection.execute(
            "UPDATE activity_users SET avatar_id = ? WHERE activity_id = ? AND id = ?",
            (avatar_id, activity_id, activity_user_id),
        )


def test_registration_assigns_avatar_and_reuses_it_for_login_and_me(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id = create_activity(client)
        register = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "头像用户", "phone": "13800000001"},
        )
        assert register.status_code == 201
        registered = register.json()
        assert AVATAR_ID_MIN <= registered["avatar_id"] <= AVATAR_ID_MAX
        assert read_avatar(settings, activity_id, registered["activity_user_id"]) == registered["avatar_id"]

        login = client.post(
            f"/api/v1/activities/{activity_id}/auth/login",
            json={"username": "头像用户", "phone": "13800000001"},
        )
        assert login.status_code == 200
        assert login.json()["avatar_id"] == registered["avatar_id"]

        me = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {registered['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["avatar_id"] == registered["avatar_id"]
    finally:
        app.dependency_overrides.clear()


def test_random_avatar_pool_includes_twentieth_id(monkeypatch) -> None:
    avatar_module = importlib.import_module("app.modules.participants.avatar")
    monkeypatch.setattr(avatar_module.secrets, "randbelow", lambda count: count - 1)

    assert avatar_module.random_avatar_id() == AVATAR_ID_MAX == 20


def test_avatar_collision_is_allowed_and_stays_stable(tmp_path: Path, monkeypatch) -> None:
    participants_router = importlib.import_module("app.modules.participants.router")
    monkeypatch.setattr(participants_router, "random_avatar_id", lambda: 16)
    client, _ = make_client(tmp_path)
    try:
        activity_id = create_activity(client)
        first = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "重复头像一", "phone": "13800000008"},
        ).json()
        second = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "重复头像二", "phone": "13800000009"},
        ).json()
        assert first["avatar_id"] == second["avatar_id"] == 16
        relogin = client.post(
            f"/api/v1/activities/{activity_id}/auth/login",
            json={"username": "重复头像二", "phone": "13800000009"},
        )
        assert relogin.status_code == 200
        assert relogin.json()["avatar_id"] == 16
    finally:
        app.dependency_overrides.clear()


def test_avatar_assignment_failure_rolls_back_registration(tmp_path: Path, monkeypatch) -> None:
    participants_router = importlib.import_module("app.modules.participants.router")
    monkeypatch.setattr(participants_router, "random_avatar_id", lambda: None)
    client, settings = make_client(tmp_path, raise_server_exceptions=False)
    try:
        activity_id = create_activity(client)
        response = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "分配失败用户", "phone": "13800000010"},
        )
        assert response.status_code == 500
        with transaction(settings) as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM activity_users WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()["count"]
        assert count == 0
    finally:
        app.dependency_overrides.clear()


def test_avatar_isolated_by_activity_and_activity_user_id(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        first_activity = create_activity(client, "活动 A")
        second_activity = create_activity(client, "活动 B")
        first = client.post(
            f"/api/v1/activities/{first_activity}/auth/register",
            json={"username": "同名用户", "phone": "13800000002"},
        ).json()
        second = client.post(
            f"/api/v1/activities/{second_activity}/auth/register",
            json={"username": "同名用户", "phone": "13800000002"},
        ).json()
        set_avatar(settings, first_activity, first["activity_user_id"], 2)
        set_avatar(settings, second_activity, second["activity_user_id"], 9)

        first_login = client.post(
            f"/api/v1/activities/{first_activity}/auth/login",
            json={"username": "同名用户", "phone": "13800000002"},
        )
        second_login = client.post(
            f"/api/v1/activities/{second_activity}/auth/login",
            json={"username": "同名用户", "phone": "13800000002"},
        )
        assert first_login.json()["avatar_id"] == 2
        assert second_login.json()["avatar_id"] == 9
    finally:
        app.dependency_overrides.clear()


def test_relogin_preserves_each_activity_avatar_and_chat_access(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        first_activity = create_activity(client, "重登活动 A")
        second_activity = create_activity(client, "重登活动 B")
        first = client.post(
            f"/api/v1/activities/{first_activity}/auth/register",
            json={"username": "重登用户", "phone": "13800000011"},
        ).json()
        second = client.post(
            f"/api/v1/activities/{second_activity}/auth/register",
            json={"username": "重登用户", "phone": "13800000012"},
        ).json()
        first_activity_avatar = 3
        second_activity_avatar = 8
        set_avatar(settings, first_activity, first["activity_user_id"], first_activity_avatar)
        set_avatar(settings, second_activity, second["activity_user_id"], second_activity_avatar)

        for activity_id, phone, expected_avatar in (
            (first_activity, "13800000011", first_activity_avatar),
            (second_activity, "13800000012", second_activity_avatar),
        ):
            relogin = client.post(
                f"/api/v1/activities/{activity_id}/auth/login",
                json={"username": "重登用户", "phone": phone},
            ).json()
            assert relogin["avatar_id"] == expected_avatar
            me = client.get(
                f"/api/v1/activities/{activity_id}/me",
                headers={"Authorization": f"Bearer {relogin['access_token']}"},
            )
            assert me.status_code == 200
            assert me.json()["avatar_id"] == expected_avatar
            chat = client.get(
                f"/api/v1/activities/{activity_id}/chat/messages",
                headers={"Authorization": f"Bearer {relogin['access_token']}"},
            )
            assert chat.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_legacy_null_avatar_is_filled_only_by_successful_login_or_me(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id = create_activity(client)
        register = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "历史用户", "phone": "13800000003"},
        ).json()
        user_id = register["activity_user_id"]
        set_avatar(settings, activity_id, user_id, None)

        invalid_login = client.post(
            f"/api/v1/activities/{activity_id}/auth/login",
            json={"username": "历史用户", "phone": "13800000000"},
        )
        assert invalid_login.status_code == 401
        assert read_avatar(settings, activity_id, user_id) is None

        login = client.post(
            f"/api/v1/activities/{activity_id}/auth/login",
            json={"username": "历史用户", "phone": "13800000003"},
        )
        assert login.status_code == 200
        assert AVATAR_ID_MIN <= login.json()["avatar_id"] <= AVATAR_ID_MAX
        assert read_avatar(settings, activity_id, user_id) == login.json()["avatar_id"]

        set_avatar(settings, activity_id, user_id, None)
        me = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {register['access_token']}"},
        )
        assert me.status_code == 200
        assert AVATAR_ID_MIN <= me.json()["avatar_id"] <= AVATAR_ID_MAX
        assert read_avatar(settings, activity_id, user_id) == me.json()["avatar_id"]
    finally:
        app.dependency_overrides.clear()


def test_old_database_migration_keeps_existing_avatar_null_until_me(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE activities (
            activity_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE activity_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT NOT NULL,
            username TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(activity_id, phone)
        );
        INSERT INTO activities
        VALUES (
            'legacy-activity', '历史活动', NULL, NULL, NULL, 'open',
            '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
        );
        INSERT INTO activity_users(activity_id, username, phone, created_at)
        VALUES ('legacy-activity', '历史用户', '13800000004', '2026-01-01T00:00:00+00:00');
        """
    )
    connection.commit()
    connection.close()

    client, settings = make_client(tmp_path, "legacy.db")
    try:
        with transaction(settings) as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(activity_users)")}
            row = connection.execute("SELECT avatar_id FROM activity_users WHERE id = 1").fetchone()
        assert "avatar_id" in columns
        assert "can_mobile_lottery" in columns
        assert row["avatar_id"] is None
        init_database(settings)

        token = create_access_token("历史用户", settings, activity_id="legacy-activity", activity_user_id=1)
        me = client.get(
            "/api/v1/activities/legacy-activity/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me.status_code == 200
        assert AVATAR_ID_MIN <= me.json()["avatar_id"] <= AVATAR_ID_MAX
        assert me.json()["can_mobile_lottery"] is False
    finally:
        app.dependency_overrides.clear()


def test_invalid_token_and_duplicate_registration_do_not_fill_avatar(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id = create_activity(client)
        registered = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "错误边界用户", "phone": "13800000006"},
        ).json()
        user_id = registered["activity_user_id"]
        set_avatar(settings, activity_id, user_id, None)
        expired_token = jwt.encode(
            {
                "sub": "错误边界用户",
                "activity_id": activity_id,
                "activity_user_id": user_id,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            settings.jwt_secret,
            algorithm="HS256",
        )
        expired = client.get(
            f"/api/v1/activities/{activity_id}/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert expired.status_code == 401
        assert read_avatar(settings, activity_id, user_id) is None

        duplicate = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "其他用户", "phone": "13800000006"},
        )
        assert duplicate.status_code == 409
        assert read_avatar(settings, activity_id, user_id) is None
    finally:
        app.dependency_overrides.clear()


def test_conditional_avatar_assignment_keeps_the_winning_value(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        activity_id = create_activity(client)
        registered = client.post(
            f"/api/v1/activities/{activity_id}/auth/register",
            json={"username": "并发用户", "phone": "13800000007"},
        ).json()
        user_id = registered["activity_user_id"]
        set_avatar(settings, activity_id, user_id, None)

        with transaction(settings) as connection:
            first = ensure_avatar_id(connection, activity_id, user_id, None)
            second = ensure_avatar_id(connection, activity_id, user_id, None)
        assert first == second
    finally:
        app.dependency_overrides.clear()


def test_cross_activity_token_does_not_fill_avatar(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    try:
        first_activity = create_activity(client, "活动 A")
        second_activity = create_activity(client, "活动 B")
        first = client.post(
            f"/api/v1/activities/{first_activity}/auth/register",
            json={"username": "跨活动用户", "phone": "13800000005"},
        ).json()
        second = client.post(
            f"/api/v1/activities/{second_activity}/auth/register",
            json={"username": "跨活动用户", "phone": "13800000005"},
        ).json()
        set_avatar(settings, second_activity, second["activity_user_id"], None)

        response = client.get(
            f"/api/v1/activities/{second_activity}/me",
            headers={"Authorization": f"Bearer {first['access_token']}"},
        )
        assert response.status_code == 403
        assert read_avatar(settings, second_activity, second["activity_user_id"]) is None
    finally:
        app.dependency_overrides.clear()
