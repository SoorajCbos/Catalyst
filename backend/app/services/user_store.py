import hashlib
import sqlite3
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "catalyst.sqlite3"
APP_ADMIN_PASSWORD_HASH = hashlib.sha256("Catalyst_@gent01".encode("utf-8")).hexdigest()


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_user_store() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                record_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                profile TEXT NOT NULL CHECK (profile IN ('platform_admin', 'organization_admin', 'member')),
                password_sha256 TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO users (
                record_id,
                username,
                email,
                organization_id,
                active,
                profile,
                password_sha256
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                email = excluded.email,
                organization_id = excluded.organization_id,
                active = excluded.active,
                profile = excluded.profile,
                password_sha256 = excluded.password_sha256
            """,
            (
                "user_app_admin_001",
                "sooraj_appAdmin",
                "sooraj@cbosit.com",
                "platform",
                1,
                "platform_admin",
                APP_ADMIN_PASSWORD_HASH,
            ),
        )


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT record_id, username, email, organization_id, active, profile, password_sha256
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if user is None or user["password_sha256"] != hash_password(password):
        return None

    return {
        "recordId": user["record_id"],
        "username": user["username"],
        "email": user["email"],
        "organizationId": user["organization_id"],
        "active": bool(user["active"]),
        "profile": user["profile"],
    }