"""Request-scoped access to the Catalyst SDK."""

from typing import Any

import zcatalyst_sdk
from fastapi import HTTPException, Request, status


def require_catalyst_app(request: Request) -> Any:
    """
    Initialize Catalyst using headers injected by AppSail.

    This will not work under plain localhost because Catalyst headers are
    only added after deployment. Local development continues using SQLite.
    """

    try:
        return zcatalyst_sdk.initialize(
            req=request,
            scope="admin",
        )
    except Exception as error:
        # Do not expose credentials or internal SDK errors to callers.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalyst services are unavailable in this environment.",
        ) from error