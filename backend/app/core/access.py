"""Authentication and role checks for protected API routes."""

from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.core.catalyst_app import get_catalyst_app
from app.core.jwt_auth import (
    SESSION_COOKIE_NAME,
    decode_access_token,
)
from app.services.user_store import get_user_by_record_id


def require_user(
    request: Request,
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> dict[str, Any]:
    """Return the current active user."""

    token = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    claims = decode_access_token(token)

    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
        )

    # Localhost reads SQLite; AppSail reads Catalyst Users.
    user = get_user_by_record_id(
        claims["sub"],
        catalyst_app,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
        )

    if not user["active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive.",
        )

    return user


def require_platform_admin(
    current_user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    """Allow only platform administrators."""

    if current_user["profile"] != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required.",
        )

    return current_user


def require_admin(
    current_user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    """Allow platform and organization administrators."""

    if current_user["profile"] not in {
        "platform_admin",
        "organization_admin",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_user