"""JWT creation and verification for authenticated sessions."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 8
SESSION_COOKIE_NAME = "catalyst_session"


def get_jwt_secret() -> str:
    """
    Read the signing secret from the environment.

    The secret is deliberately not stored in source code because anyone
    who knows it could create valid administrator tokens.
    """

    secret = os.environ.get("SESSION_SECRET")

    if not secret:
        raise RuntimeError(
            "SESSION_SECRET environment variable is required."
        )

    return secret


def create_access_token(user: dict[str, Any]) -> str:
    """
    Create a signed JWT for an authenticated user.

    The token includes only the information required to identify the user.
    Passwords and password hashes must never be included.
    """

    now = datetime.now(timezone.utc)

    payload = {
        # 'sub' is the standard JWT field identifying the token's subject.
        "sub": user["recordId"],
        "username": user["username"],
        "organizationId": user["organizationId"],
        "profile": user["profile"],
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT.

    None is returned for expired, malformed or incorrectly signed tokens.
    Callers should treat every one of these cases as unauthenticated.
    """

    try:
        return jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None