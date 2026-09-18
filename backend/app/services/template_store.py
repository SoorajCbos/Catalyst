"""Template storage: SQLite locally, Catalyst Data Store in AppSail."""

import json
import uuid
from typing import Any

from app.services.user_store import get_connection


def initialize_template_store() -> None:
    """Create the local testing table."""

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


def list_templates(
    catalyst_app: Any | None = None,
) -> list[dict[str, Any]]:
    """List templates from the active storage system."""

    if catalyst_app is not None:
        rows = _get_all_catalyst_rows(catalyst_app)
        return [_catalyst_to_response(row) for row in rows]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT record_id, name, subject, body,
                   allowed_merge_fields, active
            FROM templates
            ORDER BY name
            """
        ).fetchall()

    return [_sqlite_to_response(row) for row in rows]


def get_template(
    record_id: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Return one template."""

    if catalyst_app is not None:
        try:
            row = (
                catalyst_app.datastore()
                .table("Templates")
                .get_row(record_id)
            )
            return _catalyst_to_response(row)
        except Exception:
            return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT record_id, name, subject, body,
                   allowed_merge_fields, active
            FROM templates
            WHERE record_id = ?
            """,
            (record_id,),
        ).fetchone()

    return _sqlite_to_response(row) if row else None


def template_name_exists(
    name: str,
    excluded_record_id: str | None = None,
    catalyst_app: Any | None = None,
) -> bool:
    """Check template-name uniqueness."""

    templates = list_templates(catalyst_app)

    return any(
        template["name"].casefold() == name.casefold()
        and template["recordId"] != excluded_record_id
        for template in templates
    )


def create_template(
    name: str,
    subject: str,
    body: str,
    merge_fields: list[str],
    catalyst_app: Any | None = None,
) -> dict[str, Any]:
    """Create a reusable template."""

    if catalyst_app is not None:
        row = (
            catalyst_app.datastore()
            .table("Templates")
            .insert_row(
                {
                    "TemplateName": name,
                    "Subject": subject,
                    "Body": body,
                    "AllowedMergeFields": json.dumps(merge_fields),
                    "IsActive": True,
                }
            )
        )
        return _catalyst_to_response(row)

    record_id = f"template_{uuid.uuid4().hex[:12]}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO templates (
                record_id, name, subject, body,
                allowed_merge_fields, active
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                name,
                subject,
                body,
                json.dumps(merge_fields),
                1,
            ),
        )

    return get_template(record_id)  # type: ignore[return-value]


def update_template(
    record_id: str,
    name: str,
    subject: str,
    body: str,
    merge_fields: list[str],
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Update an existing template."""

    if catalyst_app is not None:
        try:
            catalyst_app.datastore().table("Templates").update_row(
                {
                    "ROWID": record_id,
                    "TemplateName": name,
                    "Subject": subject,
                    "Body": body,
                    "AllowedMergeFields": json.dumps(merge_fields),
                }
            )
            return get_template(record_id, catalyst_app)
        except Exception:
            return None

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE templates
            SET name = ?, subject = ?, body = ?,
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

    return get_template(record_id) if result.rowcount == 1 else None


def set_template_active(
    record_id: str,
    active: bool,
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Enable or disable a template."""

    if catalyst_app is not None:
        try:
            catalyst_app.datastore().table("Templates").update_row(
                {
                    "ROWID": record_id,
                    "IsActive": active,
                }
            )
            return get_template(record_id, catalyst_app)
        except Exception:
            return None

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE templates
            SET active = ?
            WHERE record_id = ?
            """,
            (int(active), record_id),
        )

    return get_template(record_id) if result.rowcount == 1 else None


def _get_all_catalyst_rows(
    catalyst_app: Any,
) -> list[dict[str, Any]]:
    """Read all Catalyst template rows."""

    table = catalyst_app.datastore().table("Templates")
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


def _sqlite_to_response(row) -> dict[str, Any]:
    """Convert SQLite data to the API format."""

    return {
        "recordId": row["record_id"],
        "name": row["name"],
        "subject": row["subject"],
        "body": row["body"],
        "allowedMergeFields": json.loads(row["allowed_merge_fields"]),
        "active": bool(row["active"]),
    }


def _catalyst_to_response(row: dict[str, Any]) -> dict[str, Any]:
    """Convert Catalyst data to the API format."""

    return {
        "recordId": str(row["ROWID"]),
        "name": row["TemplateName"],
        "subject": row["Subject"],
        "body": row["Body"],
        "allowedMergeFields": json.loads(
            row.get("AllowedMergeFields") or "[]"
        ),
        "active": bool(row["IsActive"]),
    }