"""Guide storage: local files/SQLite or Catalyst Data Store/File Store."""

import tempfile
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
    """Create the local testing table."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS organization_guides (
                record_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                title TEXT NOT NULL,
                guide_type TEXT NOT NULL,
                audience TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def list_organization_guides(
    organization_id: str | None = None,
    catalyst_app: Any | None = None,
) -> list[dict[str, Any]]:
    """List guides from Catalyst or the local fallback."""

    if catalyst_app is not None:
        rows = _get_all_catalyst_rows(catalyst_app)

        if organization_id:
            rows = [
                row
                for row in rows
                if _foreign_key_value(row.get("OrganizationID"))
                == organization_id
            ]

        return [
            _catalyst_to_response(row, catalyst_app)
            for row in rows
        ]

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

    return [_sqlite_to_response(row) for row in rows]


def get_organization_guide(
    record_id: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Return one guide."""

    if catalyst_app is not None:
        try:
            row = (
                catalyst_app.datastore()
                .table("OrganizationGuides")
                .get_row(record_id)
            )
            return _catalyst_to_response(row, catalyst_app)
        except Exception:
            return None

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

    return _sqlite_to_response(row) if row else None


def create_organization_guide(
    organization_id: str,
    title: str,
    guide_type: str,
    audience: str,
    content: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any]:
    """Create guide metadata and its Markdown file."""

    if catalyst_app is not None:
        file_name = _new_file_name(title, guide_type)
        file_id = _upload_file(catalyst_app, file_name, content)

        row = (
            catalyst_app.datastore()
            .table("OrganizationGuides")
            .insert_row(
                {
                    "OrganizationID": organization_id,
                    "Title": title,
                    "GuideType": guide_type,
                    "Audience": audience,
                    "FileKey": file_id,
                    "Version": 1,
                    "IsActive": True,
                }
            )
        )

        return _catalyst_to_response(row, catalyst_app)

    record_id = f"guide_{uuid.uuid4().hex[:12]}"
    path = _local_file_path(
        organization_id,
        title,
        guide_type,
        record_id,
    )

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
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Update guide metadata and create a new Markdown version."""

    existing = get_organization_guide(record_id, catalyst_app)

    if existing is None:
        return None

    if existing["organizationId"] != organization_id:
        return None

    if catalyst_app is not None:
        file_name = _new_file_name(title, guide_type)
        new_file_id = _upload_file(catalyst_app, file_name, content)

        catalyst_app.datastore().table("OrganizationGuides").update_row(
            {
                "ROWID": record_id,
                "Title": title,
                "GuideType": guide_type,
                "Audience": audience,
                "FileKey": new_file_id,
                "Version": existing["version"] + 1,
            }
        )

        # Delete the previous physical file after metadata is updated.

        return get_organization_guide(record_id, catalyst_app)

    old_path = GUIDE_ROOT / existing["filePath"]
    path = _local_file_path(
        organization_id,
        title,
        guide_type,
        record_id,
    )

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


def _folder(catalyst_app: Any):
    """Return the configured Catalyst File Store folder."""

    folder_id = os.environ.get("ORGANIZATION_GUIDE_FOLDER_ID")

    if not folder_id:
        raise RuntimeError(
            "ORGANIZATION_GUIDE_FOLDER_ID is required."
        )

    return catalyst_app.filestore().folder(int(folder_id))


def _upload_file(
    catalyst_app: Any,
    file_name: str,
    content: str,
) -> str:
    """
    Upload Markdown through a temporary file.

    Catalyst requires a real BufferedReader, so an in-memory BytesIO
    object cannot be passed directly.
    """

    temporary_path = ""

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".md",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content.encode("utf-8"))
            temporary_path = temporary_file.name

        # open(..., "rb") returns the BufferedReader required by the SDK.
        with open(temporary_path, "rb") as markdown_file:
            result = _folder(catalyst_app).upload_file(
                file_name,
                markdown_file,
            )

        return str(result["id"])
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
def _download_file(
    catalyst_app: Any,
    file_id: str,
) -> str:
    """Download Markdown content."""

    data = _folder(catalyst_app).download_file(int(file_id))
    return data.decode("utf-8")


def _delete_file(
    catalyst_app: Any,
    file_id: str,
) -> None:
    """Delete an old Markdown file version."""

    if file_id:
        _folder(catalyst_app).delete_file(int(file_id))


def _get_all_catalyst_rows(
    catalyst_app: Any,
) -> list[dict[str, Any]]:
    """Read all guide metadata rows."""

    table = catalyst_app.datastore().table("OrganizationGuides")
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


def _safe_file_part(value: str) -> str:
    """Create a safe file-name component."""

    cleaned = SAFE_NAME_PATTERN.sub("-", value.strip()).strip("-")
    return cleaned or "guide"


def _new_file_name(title: str, guide_type: str) -> str:
    """Create a unique Markdown file name."""

    return (
        f"{_safe_file_part(title)}-"
        f"{_safe_file_part(guide_type)}-"
        f"{uuid.uuid4().hex[:12]}.md"
    )


def _local_file_path(
    organization_id: str,
    title: str,
    guide_type: str,
    record_id: str,
) -> Path:
    """Build the local testing path."""

    directory = GUIDE_ROOT / _safe_file_part(organization_id)
    file_name = (
        f"{_safe_file_part(title)}-"
        f"{_safe_file_part(guide_type)}-{record_id}.md"
    )
    return directory / file_name


def _foreign_key_value(value: Any) -> str:
    """Normalize a Catalyst foreign-key value."""

    if isinstance(value, dict):
        return str(value.get("ROWID", ""))

    return str(value or "")


def _sqlite_to_response(row) -> dict[str, Any]:
    """Convert local data to the API format."""

    return {
        "recordId": row["record_id"],
        "organizationId": row["organization_id"],
        "title": row["title"],
        "guideType": row["guide_type"],
        "audience": row["audience"],
        "fileName": row["file_name"],
        "filePath": row["file_path"],
        "content": row["content"],
        "version": 1,
        "active": True,
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def _catalyst_to_response(
    row: dict[str, Any],
    catalyst_app: Any,
) -> dict[str, Any]:
    """Convert Catalyst metadata and download its Markdown."""

    file_id = str(row["FileKey"])
    file_name = (
        f"{_safe_file_part(row['Title'])}-"
        f"{_safe_file_part(row['GuideType'])}.md"
    )

    return {
        "recordId": str(row["ROWID"]),
        "organizationId": _foreign_key_value(
            row.get("OrganizationID")
        ),
        "title": row["Title"],
        "guideType": row["GuideType"],
        "audience": row["Audience"],
        "fileName": file_name,
        "filePath": file_id,
        "content": _download_file(catalyst_app, file_id),
        "version": int(row["Version"]),
        "active": bool(row["IsActive"]),
        "createdAt": str(row.get("CREATEDTIME", "")),
        "updatedAt": str(row.get("MODIFIEDTIME", "")),
    }