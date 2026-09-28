"""Chat session storage: SQLite locally, Catalyst Data Store in AppSail."""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.user_store import get_connection

SESSION_TABLE = "ChatSessions"
MESSAGE_TABLE = "ChatMessages"
MAX_TITLE_LENGTH = 60


def _now() -> str:
    """Return the current UTC time in Catalyst-compatible format."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _safe_id(value: str) -> str:
    """Allow only numeric Catalyst IDs inside ZCQL queries."""

    value = str(value).strip()

    if not value.isdigit():
        raise ValueError("Invalid record ID.")

    return value


def _zcql(catalyst_app: Any, query: str, table: str) -> list[dict[str, Any]]:
    """Run a ZCQL query and unwrap rows."""

    rows = catalyst_app.zcql().execute_query(query) or []
    return [row.get(table, row) for row in rows]


def make_title(message: str) -> str:
    """Create a short session title from the first message."""

    title = " ".join(message.split())

    if len(title) <= MAX_TITLE_LENGTH:
        return title

    return title[: MAX_TITLE_LENGTH - 3] + "..."


def initialize_chat_session_store() -> None:
    """Create local SQLite tables used during development."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                organization_id TEXT,
                agent_key TEXT NOT NULL,
                title TEXT NOT NULL,
                last_message_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                record_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )


def create_session(
    user_id: str,
    organization_id: str,
    agent_key: str,
    title: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any]:
    """Create a new chat session."""

    now = _now()

    if catalyst_app is not None:
        row = (
            catalyst_app.datastore()
            .table(SESSION_TABLE)
            .insert_row(
                {
                    "UserID": user_id,
                    "OrganizationID": organization_id,
                    "AgentKey": agent_key,
                    "Title": title,
                    "LastMessageAt": now,
                }
            )
        )
        return _catalyst_session(row)

    record_id = f"session_{uuid.uuid4().hex[:12]}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO chat_sessions (
                record_id, user_id, organization_id,
                agent_key, title, last_message_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (record_id, user_id, organization_id, agent_key, title, now),
        )

    return {
        "sessionId": record_id,
        "userId": user_id,
        "organizationId": organization_id,
        "agentKey": agent_key,
        "title": title,
        "lastMessageAt": now,
    }


def get_session(
    session_id: str,
    user_id: str,
    catalyst_app: Any | None = None,
) -> dict[str, Any] | None:
    """Return a session only if it belongs to this user."""

    session: dict[str, Any] | None = None

    if catalyst_app is not None:
        try:
            row = (
                catalyst_app.datastore()
                .table(SESSION_TABLE)
                .get_row(_safe_id(session_id))
            )
            session = _catalyst_session(row)
        except Exception:
            return None
    else:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM chat_sessions WHERE record_id = ?",
                (session_id,),
            ).fetchone()

        session = _sqlite_session(row) if row else None

    if session is None or session["userId"] != user_id:
        return None

    return session


def list_sessions(
    user_id: str,
    catalyst_app: Any | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List a user's sessions, newest first."""

    if catalyst_app is not None:
        rows = _zcql(
            catalyst_app,
            f"SELECT * FROM {SESSION_TABLE} "
            f"WHERE UserID = '{_safe_id(user_id)}' "
            "ORDER BY LastMessageAt DESC",
            SESSION_TABLE,
        )
        return [_catalyst_session(row) for row in rows[:limit]]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM chat_sessions
            WHERE user_id = ?
            ORDER BY last_message_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [_sqlite_session(row) for row in rows]


def list_messages(
    session_id: str,
    catalyst_app: Any | None = None,
) -> list[dict[str, Any]]:
    """List a session's messages, oldest first."""

    if catalyst_app is not None:
        rows = _zcql(
            catalyst_app,
            f"SELECT * FROM {MESSAGE_TABLE} "
            f"WHERE SessionID = '{_safe_id(session_id)}' "
            "ORDER BY CREATEDTIME ASC",
            MESSAGE_TABLE,
        )
        return [_catalyst_message(row) for row in rows]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

    return [_sqlite_message(row) for row in rows]


def add_message(
    session_id: str,
    sender: str,
    content: str,
    tokens_used: int = 0,
    catalyst_app: Any | None = None,
) -> None:
    """Save a message and update the session's last activity time."""

    now = _now()

    if catalyst_app is not None:
        catalyst_app.datastore().table(MESSAGE_TABLE).insert_row(
            {
                "SessionID": session_id,
                "Sender": sender,
                "Content": content,
                "TokensUsed": tokens_used,
            }
        )
        catalyst_app.datastore().table(SESSION_TABLE).update_row(
            {"ROWID": session_id, "LastMessageAt": now}
        )
        return

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO chat_messages (
                record_id, session_id, sender, content,
                tokens_used, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"message_{uuid.uuid4().hex[:12]}",
                session_id,
                sender,
                content,
                tokens_used,
                now,
            ),
        )
        connection.execute(
            "UPDATE chat_sessions SET last_message_at = ? WHERE record_id = ?",
            (now, session_id),
        )


def _catalyst_session(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sessionId": str(row["ROWID"]),
        "userId": str(row.get("UserID", "")),
        "organizationId": str(row.get("OrganizationID") or ""),
        "agentKey": str(row.get("AgentKey", "")),
        "title": str(row.get("Title", "")),
        "lastMessageAt": str(
            row.get("LastMessageAt") or row.get("CREATEDTIME", "")
        ),
    }


def _catalyst_message(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "messageId": str(row["ROWID"]),
        "sessionId": str(row.get("SessionID", "")),
        "sender": str(row.get("Sender", "agent")),
        "content": str(row.get("Content", "")),
        "tokensUsed": int(row.get("TokensUsed") or 0),
        "createdAt": str(row.get("CREATEDTIME", "")),
    }


def _sqlite_session(row) -> dict[str, Any]:
    return {
        "sessionId": row["record_id"],
        "userId": row["user_id"],
        "organizationId": row["organization_id"] or "",
        "agentKey": row["agent_key"],
        "title": row["title"],
        "lastMessageAt": row["last_message_at"],
    }


def _sqlite_message(row) -> dict[str, Any]:
    return {
        "messageId": row["record_id"],
        "sessionId": row["session_id"],
        "sender": row["sender"],
        "content": row["content"],
        "tokensUsed": row["tokens_used"],
        "createdAt": row["created_at"],
    }