"""Endpoint used to verify Catalyst Data Store connectivity."""

from typing import Any

from fastapi import APIRouter, Depends

from app.core.access import require_platform_admin
from app.core.catalyst_app import require_catalyst_app

router = APIRouter()


@router.get("")
def get_catalyst_status(
    _: dict[str, Any] = Depends(require_platform_admin),
    catalyst_app: Any = Depends(require_catalyst_app),
) -> dict[str, Any]:
    """
    Read at most one Organizations row.

    Success proves that AppSail injected valid Catalyst credentials and
    that the backend can access the Data Store.
    """

    result = (
        catalyst_app
        .datastore()
        .table("Organizations")
        .get_paged_rows(max_rows=1)
    )

    return {
        "connected": True,
        "organizationRowsRead": len(result.get("data", [])),
    }