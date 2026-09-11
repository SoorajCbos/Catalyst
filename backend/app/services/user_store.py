"""Local user storage used while developing and testing."""

import hashlib
import secrets
import sqlite3
import string
import uuid
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "catalyst.sqlite3"

# Predictable platform-admin account used only for local testing.
APP_ADMIN_PASSWORD_HASH = hashlib.sha256(
    "Catalyst_@gent01".encode("utf-8")
).hexdigest()


def get_connection() -> sqlite3.Connection:
    """Open the local SQLite database and return rows by column name."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_user_store() -> None:
    """Create the local users table and test platform-admin account."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                record_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                profile TEXT NOT NULL CHECK (
                    profile IN (
                        'platform_admin',
                        'organization_admin',
                        'member'
                    )
                ),
                password_sha256 TEXT NOT NULL
            )
            """
        )

        # Keep one predictable account for local login testing.
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
    """
    Hash a password before saving it.

    This retains compatibility with the current testing implementation.
    Plain passwords are never stored in the database.
    """

    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_default_password(length: int = 12) -> str:
    """Generate a random default password for a new user."""

    characters = string.ascii_letters + string.digits

    return "".join(secrets.choice(characters) for _ in range(length))


def username_exists(username: str) -> bool:
    """Check whether a username has already been assigned."""

    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    return row is not None


def list_users(organization_id: str | None = None) -> list[dict[str, Any]]:
    """Return users without exposing their password hashes."""

    query = """
        SELECT record_id, username, email, organization_id, active, profile
        FROM users
    """
    parameters: tuple[str, ...] = ()

    if organization_id:
        query += " WHERE organization_id = ?"
        parameters = (organization_id,)

    query += " ORDER BY username"

    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [_user_to_response(row) for row in rows]


def create_user(
    username: str,
    email: str,
    organization_id: str,
    profile: str,
) -> dict[str, Any]:
    """
    Create a user with a generated default password.

    Only the password hash is stored. The plain password is returned once
    so the administrator can provide it to the new user.
    """

    record_id = f"user_{uuid.uuid4().hex[:12]}"
    default_password = generate_default_password()

    with get_connection() as connection:
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
            """,
            (
                record_id,
                username,
                email,
                organization_id,
                1,
                profile,
                hash_password(default_password),
            ),
        )

    return {
        "recordId": record_id,
        "username": username,
        "email": email,
        "organizationId": organization_id,
        "active": True,
        "profile": profile,
        "defaultPassword": default_password,
    }


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Validate a username and password against the local user table."""

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT
                record_id,
                username,
                email,
                organization_id,
                active,
                profile,
                password_sha256
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if user is None or user["password_sha256"] != hash_password(password):
        return None

    return _user_to_response(user)


def change_user_password(
    username: str,
    current_password: str,
    new_password: str,
) -> bool:
    """
    Replace a user's password after validating the current password.

    This works for both a generated default password and an ordinary
    password. False is returned when the username or current password is
    incorrect.
    """

    user = authenticate_user(username, current_password)

    if user is None:
        return False

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE users
            SET password_sha256 = ?
            WHERE username = ?
            """,
            (hash_password(new_password), username),
        )

    return result.rowcount == 1


def _user_to_response(user) -> dict[str, Any]:
    """Convert a SQLite user row into the API response format."""

    return {
        "recordId": user["record_id"],
        "username": user["username"],
        "email": user["email"],
        "organizationId": user["organization_id"],
        "active": bool(user["active"]),
        "profile": user["profile"],
    }