"""Organization storage for SQLite locally and Catalyst in AppSail."""

import uuid
from typing import Any

from app.services.user_store import get_connection


def initialize_organization_store() -> None:
    """Create the local SQLite table used during development."""

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


def list_organizations(
    catalyst_app: Any | None = None,
) -> list[dict[str, Any]]:
    """Return organizations from the active storage system."""

    if catalyst_app is not None:
        rows = _get_all_catalyst_rows(
            catalyst_app,
            "Organizations",
        )
        return [_catalyst_to_response(row) for row in rows]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT record_id, name, tier, member_limit
            FROM organizations
            ORDER BY name
            """
        ).fetchall()

    return [_sqlite_to_response(row) for row in rows]


def get_organization(
    record_id: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Return one organization or None."""

    if catalyst_app is not None:
        try:
            row = (
                catalyst_app.datastore()
                .table("Organizations")
                .get_row(record_id)
            )
            return _catalyst_to_response(row)
        except Exception:
            return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT record_id, name, tier, member_limit
            FROM organizations
            WHERE record_id = ?
            """,
            (record_id,),
        ).fetchone()

    return _sqlite_to_response(row) if row else None


def count_organization_users(
    organization_id: str,
    catalyst_app: Any | None = None,
) -> int:
    """Count users assigned to an organization."""

    if catalyst_app is not None:
        rows = _get_all_catalyst_rows(catalyst_app, "Users")
        return sum(
            1
            for row in rows
            if str(row.get("OrgID", "")) == organization_id
        )

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


def organization_name_exists(
    name: str,
    catalyst_app: Any | None = None,
) -> bool:
    """Check whether an organization name already exists."""

    if catalyst_app is not None:
        return any(
            organization["name"].casefold() == name.casefold()
            for organization in list_organizations(catalyst_app)
        )

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
    catalyst_app: Any | None = None,
) -> dict[str, Any]:
    """Create an organization in the active storage system."""

    if catalyst_app is not None:
        row = (
            catalyst_app.datastore()
            .table("Organizations")
            .insert_row(
                {
                    "OrgName": name,
                    "Tier": tier,
                    "MemberLimit": member_limit,
                }
            )
        )
        return _catalyst_to_response(row)

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


def _get_all_catalyst_rows(
    catalyst_app: Any,
    table_name: str,
) -> list[dict[str, Any]]:
    """Read all currently available rows using Catalyst pagination."""

    table = catalyst_app.datastore().table(table_name)
    rows: list[dict[str, Any]] = []
    next_token: str | None = None

    while True:
        if next_token:
            result = table.get_paged_rows(
                next_token=next_token,
                max_rows=200,
            )
        else:
            result = table.get_paged_rows(max_rows=200)

        rows.extend(result.get("data", []))

        if not result.get("more_records"):
            break

        next_token = result.get("next_token")

        if not next_token:
            break

    return rows


def _sqlite_to_response(row) -> dict[str, Any]:
    """Convert a SQLite row to the public API format."""

    return {
        "recordId": row["record_id"],
        "name": row["name"],
        "tier": row["tier"],
        "memberLimit": row["member_limit"],
    }


def _catalyst_to_response(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a Catalyst row to the same public API format."""

    return {
        "recordId": str(row["ROWID"]),
        "name": row["OrgName"],
        "tier": row["Tier"],
        "memberLimit": int(row["MemberLimit"]),
    }