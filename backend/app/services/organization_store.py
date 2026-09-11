"""Local organization storage used while developing and testing."""

import uuid
from typing import Any

from app.services.user_store import get_connection


def initialize_organization_store() -> None:
    """Create the local organizations table when necessary."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                record_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                tier TEXT NOT NULL,
                member_limit INTEGER NOT NULL
            )
            """
        )


def list_organizations() -> list[dict[str, Any]]:
    """Return all organizations ordered by name."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT record_id, name, tier, member_limit
            FROM organizations
            ORDER BY name
            """
        ).fetchall()

    return [_to_response(row) for row in rows]


def get_organization(record_id: str) -> dict[str, Any] | None:
    """Return one organization, or None when it does not exist."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT record_id, name, tier, member_limit
            FROM organizations
            WHERE record_id = ?
            """,
            (record_id,),
        ).fetchone()

    return _to_response(row) if row else None


def count_organization_users(organization_id: str) -> int:
    """
    Count users assigned to an organization.

    The User page uses this count to stop new users from being created
    after the organization's purchased member limit has been reached.
    """

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            WHERE organization_id = ?
            """,
            (organization_id,),
        ).fetchone()

    return int(row["total"])


def organization_name_exists(name: str) -> bool:
    """Check whether an organization name already exists."""

    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM organizations WHERE name = ?",
            (name,),
        ).fetchone()

    return row is not None


def create_organization(
    name: str,
    tier: str,
    member_limit: int,
) -> dict[str, Any]:
    """Create and return an organization."""

    record_id = f"org_{uuid.uuid4().hex[:12]}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO organizations (
                record_id,
                name,
                tier,
                member_limit
            )
            VALUES (?, ?, ?, ?)
            """,
            (record_id, name, tier, member_limit),
        )

    return {
        "recordId": record_id,
        "name": name,
        "tier": tier,
        "memberLimit": member_limit,
    }


def _to_response(row) -> dict[str, Any]:
    """Convert a SQLite row to the frontend response format."""

    return {
        "recordId": row["record_id"],
        "name": row["name"],
        "tier": row["tier"],
        "memberLimit": row["member_limit"],
    }