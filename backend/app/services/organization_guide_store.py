import os
import re
import uuid
from pathlib import Path
from typing import Any

from app.services.user_store import get_connection

DEFAULT_GUIDE_ROOT = Path.home() / ".catalyst" / "organization-guides"
GUIDE_ROOT = Path(
    os.environ.get("ORGANIZATION_GUIDE_STORAGE_PATH", DEFAULT_GUIDE_ROOT)
).expanduser()
SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


def initialize_organization_guide_store() -> None:
    """Create the guide metadata table used by the organization guide editor."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS organization_guides (
                record_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                title TEXT NOT NULL,
                guide_type TEXT NOT NULL CHECK (
                    guide_type IN ('main', 'profile', 'role')
                ),
                audience TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _safe_file_part(value: str) -> str:
    cleaned = SAFE_NAME_PATTERN.sub("-", value.strip()).strip("-")
    return cleaned or "guide"


def _file_path(
    organization_id: str,
    title: str,
    guide_type: str,
    record_id: str,
) -> Path:
    organization_directory = GUIDE_ROOT / _safe_file_part(organization_id)
    file_name = (
        f"{_safe_file_part(title)}-"
        f"{_safe_file_part(guide_type)}-{record_id}.md"
    )
    return organization_directory / file_name


def list_organization_guides(
    organization_id: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT record_id, organization_id, title, guide_type, audience,
               file_name, file_path, content, created_at, updated_at
        FROM organization_guides
    """
    parameters: tuple[str, ...] = ()

    if organization_id:
        query += " WHERE organization_id = ?"
        parameters = (organization_id,)

    query += " ORDER BY organization_id, title"

    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [_to_response(row) for row in rows]


def get_organization_guide(record_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT record_id, organization_id, title, guide_type, audience,
                   file_name, file_path, content, created_at, updated_at
            FROM organization_guides
            WHERE record_id = ?
            """,
            (record_id,),
        ).fetchone()

    return _to_response(row) if row else None


def create_organization_guide(
    organization_id: str,
    title: str,
    guide_type: str,
    audience: str,
    content: str,
) -> dict[str, Any]:
    record_id = f"guide_{uuid.uuid4().hex[:12]}"
    path = _file_path(organization_id, title, guide_type, record_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO organization_guides (
                record_id, organization_id, title, guide_type, audience,
                file_name, file_path, content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                organization_id,
                title,
                guide_type,
                audience,
                path.name,
                str(path.relative_to(GUIDE_ROOT)),
                content,
            ),
        )

    return get_organization_guide(record_id)  # type: ignore[return-value]


def update_organization_guide(
    record_id: str,
    organization_id: str,
    title: str,
    guide_type: str,
    audience: str,
    content: str,
) -> dict[str, Any] | None:
    existing = get_organization_guide(record_id)

    if existing is None or existing["organizationId"] != organization_id:
        return None

    old_path = GUIDE_ROOT / existing["filePath"]
    path = _file_path(organization_id, title, guide_type, record_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    if old_path != path and old_path.exists():
        old_path.unlink()

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE organization_guides
            SET title = ?, guide_type = ?, audience = ?, file_name = ?,
                file_path = ?, content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE record_id = ? AND organization_id = ?
            """,
            (
                title,
                guide_type,
                audience,
                path.name,
                str(path.relative_to(GUIDE_ROOT)),
                content,
                record_id,
                organization_id,
            ),
        )

    return get_organization_guide(record_id)


def _to_response(row) -> dict[str, Any]:
    return {
        "recordId": row["record_id"],
        "organizationId": row["organization_id"],
        "title": row["title"],
        "guideType": row["guide_type"],
        "audience": row["audience"],
        "fileName": row["file_name"],
        "filePath": row["file_path"],
        "content": row["content"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }