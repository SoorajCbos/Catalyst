"""Request-scoped access to the Catalyst SDK."""

from typing import Any

import zcatalyst_sdk
from fastapi import HTTPException, Request, status


def get_catalyst_app(request: Request) -> Any | None:
    """
    Return a Catalyst app inside AppSail.

    Local Uvicorn requests lack Catalyst headers, so None is returned and
    service files can use SQLite for local testing.
    """

    try:
        return zcatalyst_sdk.initialize(
            req=request,
            scope="admin",
        )
    except Exception:
        return None


def require_catalyst_app(request: Request) -> Any:
    """Require Catalyst instead of allowing the SQLite fallback."""

    catalyst_app = get_catalyst_app(request)

    if catalyst_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalyst services are unavailable in this environment.",
        )

    return catalyst_app