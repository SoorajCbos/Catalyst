"""Reusable authentication and role checks for protected API routes."""

from typing import Any

from fastapi import HTTPException, Request, status

from app.core.jwt_auth import (
    SESSION_COOKIE_NAME,
    decode_access_token,
)
from app.services.user_store import get_user_by_record_id


def require_user(request: Request) -> dict[str, Any]:
    """Return the current active user or reject the request."""

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

    user = get_user_by_record_id(claims["sub"])

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


def require_platform_admin(request: Request) -> dict[str, Any]:
    """Allow only active platform administrators."""

    user = require_user(request)

    if user["profile"] != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required.",
        )

    return user

def require_admin(request: Request) -> dict[str, Any]:
    """Allow platform administrators and organization administrators."""

    user = require_user(request)

    if user["profile"] not in {
        "platform_admin",
        "organization_admin",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return user