"""Local template storage used while developing and testing."""

import json
import uuid
from typing import Any

from app.services.user_store import get_connection


def initialize_template_store() -> None:
    """Create the local templates table when necessary."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                record_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                allowed_merge_fields TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )


def list_templates() -> list[dict[str, Any]]:
    """Return every template ordered by name."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                record_id,
                name,
                subject,
                body,
                allowed_merge_fields,
                active
            FROM templates
            ORDER BY name
            """
        ).fetchall()

    return [_to_response(row) for row in rows]


def get_template(record_id: str) -> dict[str, Any] | None:
    """Return one template or None when it does not exist."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                record_id,
                name,
                subject,
                body,
                allowed_merge_fields,
                active
            FROM templates
            WHERE record_id = ?
            """,
            (record_id,),
        ).fetchone()

    return _to_response(row) if row else None


def template_name_exists(
    name: str,
    excluded_record_id: str | None = None,
) -> bool:
    """
    Check whether a template name already exists.

    excluded_record_id is used while editing so a template does not
    conflict with its own existing name.
    """

    with get_connection() as connection:
        if excluded_record_id:
            row = connection.execute(
                """
                SELECT 1
                FROM templates
                WHERE name = ? AND record_id != ?
                """,
                (name, excluded_record_id),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT 1 FROM templates WHERE name = ?",
                (name,),
            ).fetchone()

    return row is not None


def create_template(
    name: str,
    subject: str,
    body: str,
    merge_fields: list[str],
) -> dict[str, Any]:
    """Create and return a reusable template."""

    record_id = f"template_{uuid.uuid4().hex[:12]}"

    # SQLite does not have a list type, so store the field names as JSON.
    stored_merge_fields = json.dumps(merge_fields)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO templates (
                record_id,
                name,
                subject,
                body,
                allowed_merge_fields,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                name,
                subject,
                body,
                stored_merge_fields,
                1,
            ),
        )

    return {
        "recordId": record_id,
        "name": name,
        "subject": subject,
        "body": body,
        "allowedMergeFields": merge_fields,
        "active": True,
    }


def update_template(
    record_id: str,
    name: str,
    subject: str,
    body: str,
    merge_fields: list[str],
) -> dict[str, Any] | None:
    """Update a template and return its new values."""

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE templates
            SET
                name = ?,
                subject = ?,
                body = ?,
                allowed_merge_fields = ?
            WHERE record_id = ?
            """,
            (
                name,
                subject,
                body,
                json.dumps(merge_fields),
                record_id,
            ),
        )

    if result.rowcount != 1:
        return None

    return get_template(record_id)


def set_template_active(
    record_id: str,
    active: bool,
) -> dict[str, Any] | None:
    """Enable or disable a template without deleting it."""

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE templates
            SET active = ?
            WHERE record_id = ?
            """,
            (int(active), record_id),
        )

    if result.rowcount != 1:
        return None

    return get_template(record_id)


def _to_response(row) -> dict[str, Any]:
    """Convert a SQLite row into the frontend response format."""

    return {
        "recordId": row["record_id"],
        "name": row["name"],
        "subject": row["subject"],
        "body": row["body"],
        "allowedMergeFields": json.loads(row["allowed_merge_fields"]),
        "active": bool(row["active"]),
    }