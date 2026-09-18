"""User storage: SQLite locally, Catalyst Data Store in AppSail."""

import hashlib
import secrets
import sqlite3
import string
import uuid
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "catalyst.sqlite3"

APP_ADMIN_PASSWORD_HASH = hashlib.sha256(
    "Catalyst_@gent01".encode("utf-8")
).hexdigest()


def get_connection() -> sqlite3.Connection:
    """Open the local testing database."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_user_store() -> None:
    """Create and seed the local testing table."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                record_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                profile TEXT NOT NULL,
                password_sha256 TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)")
        }

        if "must_change_password" not in columns:
            connection.execute(
                """
                ALTER TABLE users
                ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0
                """
            )

        connection.execute(
            """
            INSERT INTO users (
                record_id, username, email, organization_id, active,
                profile, password_sha256, must_change_password
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                email = excluded.email,
                organization_id = excluded.organization_id,
                active = excluded.active,
                profile = excluded.profile,
                password_sha256 = excluded.password_sha256,
                must_change_password = excluded.must_change_password
            """,
            (
                "user_app_admin_001",
                "sooraj_appAdmin",
                "sooraj@cbosit.com",
                "platform",
                1,
                "platform_admin",
                APP_ADMIN_PASSWORD_HASH,
                0,
            ),
        )


def hash_password(password: str) -> str:
    """Hash a password using the current project format."""

    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_default_password(length: int = 12) -> str:
    """Generate a secure temporary password."""

    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))


def username_exists(
    username: str,
    catalyst_app: Any | None = None,
) -> bool:
    """Check username uniqueness."""

    return any(
        user["username"].casefold() == username.casefold()
        for user in list_users(catalyst_app=catalyst_app)
    )


def list_users(
    organization_id: str | None = None,
    catalyst_app: Any | None = None,
) -> list[dict[str, Any]]:
    """List users, optionally filtered by organization."""

    if catalyst_app is not None:
        rows = _get_all_catalyst_rows(catalyst_app, "Users")
        users = [_catalyst_to_response(row) for row in rows]

        if organization_id:
            users = [
                user
                for user in users
                if user["organizationId"] == organization_id
            ]

        return sorted(users, key=lambda user: user["username"].casefold())

    query = """
        SELECT record_id, username, email, organization_id, active,
               profile, must_change_password
        FROM users
    """
    parameters: tuple[str, ...] = ()

    if organization_id:
        query += " WHERE organization_id = ?"
        parameters = (organization_id,)

    query += " ORDER BY username"

    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [_sqlite_to_response(row) for row in rows]


def create_user(
    username: str,
    email: str,
    organization_id: str,
    profile: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any]:
    """Create a user and return their temporary password once."""

    default_password = generate_default_password()

    if catalyst_app is not None:
        row = (
            catalyst_app.datastore()
            .table("Users")
            .insert_row(
                {
                    "Username": username,
                    "Email": email,
                    "PasswordHash": hash_password(default_password),
                    "Profile": profile,
                    "OrgID": organization_id,
                    "IsActive": True,
                    "MustChangePassword": True,
                }
            )
        )

        response = _catalyst_to_response(row)
        response["defaultPassword"] = default_password
        return response

    record_id = f"user_{uuid.uuid4().hex[:12]}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                record_id, username, email, organization_id, active,
                profile, password_sha256, must_change_password
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                username,
                email,
                organization_id,
                1,
                profile,
                hash_password(default_password),
                1,
            ),
        )

    return {
        "recordId": record_id,
        "username": username,
        "email": email,
        "organizationId": organization_id,
        "active": True,
        "profile": profile,
        "mustChangePassword": True,
        "defaultPassword": default_password,
    }


def get_user_by_record_id(
    record_id: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Find a user by SQLite ID or Catalyst ROWID."""

    if catalyst_app is not None:
        try:
            row = (
                catalyst_app.datastore()
                .table("Users")
                .get_row(record_id)
            )
            return _catalyst_to_response(row)
        except Exception:
            return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT record_id, username, email, organization_id, active,
                   profile, must_change_password
            FROM users
            WHERE record_id = ?
            """,
            (record_id,),
        ).fetchone()

    return _sqlite_to_response(row) if row else None


def authenticate_user(
    username: str,
    password: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Authenticate against the active storage system."""

    if catalyst_app is not None:
        rows = _get_all_catalyst_rows(catalyst_app, "Users")

        user = next(
            (
                row
                for row in rows
                if str(row.get("Username", "")).casefold()
                == username.casefold()
            ),
            None,
        )

        if user is None:
            return None

        if user.get("PasswordHash") != hash_password(password):
            return None

        return _catalyst_to_response(user)

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT record_id, username, email, organization_id, active,
                   profile, password_sha256, must_change_password
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if user is None or user["password_sha256"] != hash_password(password):
        return None

    return _sqlite_to_response(user)


def change_user_password(
    username: str,
    current_password: str,
    new_password: str,
    catalyst_app: Any | None = None,
) -> bool:
    """Change a password and clear the temporary-password flag."""

    user = authenticate_user(username, current_password, catalyst_app)

    if user is None:
        return False

    if catalyst_app is not None:
        catalyst_app.datastore().table("Users").update_row(
            {
                "ROWID": user["recordId"],
                "PasswordHash": hash_password(new_password),
                "MustChangePassword": False,
            }
        )
        return True

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE users
            SET password_sha256 = ?, must_change_password = 0
            WHERE username = ?
            """,
            (hash_password(new_password), username),
        )

    return result.rowcount == 1


def _get_all_catalyst_rows(
    catalyst_app: Any,
    table_name: str,
) -> list[dict[str, Any]]:
    """Read all rows using Catalyst pagination."""

    table = catalyst_app.datastore().table(table_name)
    rows: list[dict[str, Any]] = []
    next_token: str | None = None

    while True:
        result = (
            table.get_paged_rows(next_token=next_token, max_rows=200)
            if next_token
            else table.get_paged_rows(max_rows=200)
        )

        rows.extend(result.get("data", []))

        if not result.get("more_records"):
            break

        next_token = result.get("next_token")

        if not next_token:
            break

    return rows


def _foreign_key_value(value: Any) -> str:
    """Normalize a Catalyst foreign-key value."""

    if isinstance(value, dict):
        return str(value.get("ROWID", ""))

    return str(value or "")


def _sqlite_to_response(user) -> dict[str, Any]:
    """Convert SQLite data to the API format."""

    return {
        "recordId": user["record_id"],
        "username": user["username"],
        "email": user["email"],
        "organizationId": user["organization_id"],
        "active": bool(user["active"]),
        "profile": user["profile"],
        "mustChangePassword": bool(user["must_change_password"]),
    }


def _catalyst_to_response(user: dict[str, Any]) -> dict[str, Any]:
    """Convert Catalyst data to the API format."""

    return {
        "recordId": str(user["ROWID"]),
        "username": user["Username"],
        "email": user["Email"],
        "organizationId": _foreign_key_value(user.get("OrgID")),
        "active": bool(user["IsActive"]),
        "profile": user["Profile"],
        "mustChangePassword": bool(user["MustChangePassword"]),
    }