"""Audit storage for AI agent calls."""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.user_store import get_connection


def _now() -> str:
    """Return the current UTC time in Catalyst-compatible format."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def initialize_agent_call_store() -> None:
    """Create the local SQLite table used during development."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_calls (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                organization_id TEXT,
                agent_name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT
            )
            """
        )


def start_agent_call(
    user_id: str,
    organization_id: str,
    agent_name: str,
    prompt: str,
    catalyst_app: Any | None = None,
) -> str:
    """Create a running audit record and return its ID."""

    started_at = _now()

    if catalyst_app is not None:
        row = (
            catalyst_app.datastore()
            .table("AgentCalls")
            .insert_row(
                {
                    "UserID": user_id,
                    "OrganizationID": organization_id,
                    "AgentName": agent_name,
                    "Prompt": prompt,
                    "Status": "running",
                    "TokensUsed": 0,
                    "StartedAt": started_at,
                }
            )
        )

        return str(row["ROWID"])

    record_id = f"call_{uuid.uuid4().hex[:12]}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO agent_calls (
                record_id,
                user_id,
                organization_id,
                agent_name,
                prompt,
                status,
                tokens_used,
                started_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                user_id,
                organization_id,
                agent_name,
                prompt,
                "running",
                0,
                started_at,
            ),
        )

    return record_id


def complete_agent_call(
    record_id: str,
    status: str,
    tokens_used: int = 0,
    error_message: str = "",
    catalyst_app: Any | None = None,
) -> None:
    """Finish an audit record after the agent succeeds or fails."""

    completed_at = _now()

    if catalyst_app is not None:
        catalyst_app.datastore().table("AgentCalls").update_row(
            {
                "ROWID": record_id,
                "Status": status,
                "TokensUsed": tokens_used,
                "CompletedAt": completed_at,
                "ErrorMessage": error_message,
            }
        )
        return

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE agent_calls
            SET
                status = ?,
                tokens_used = ?,
                completed_at = ?,
                error_message = ?
            WHERE record_id = ?
            """,
            (
                status,
                tokens_used,
                completed_at,
                error_message,
                record_id,
            ),
        )