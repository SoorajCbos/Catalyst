from fastapi import APIRouter, Depends

from app.api.v1.routes import (
    auth,
    catalyst_status,
    health,
    organization_guides,
    organizations,
    templates,
    users,
)
from app.core.access import require_platform_admin

api_router = APIRouter()

# Public routes.
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

# Platform administrator routes.
api_router.include_router(
    organizations.router,
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(require_platform_admin)],
)

api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["templates"],
    dependencies=[Depends(require_platform_admin)],
)

api_router.include_router(
    organization_guides.router,
    prefix="/organization-guides",
    tags=["organization-guides"],
    dependencies=[Depends(require_platform_admin)],
)

# User routes enforce their own organization-specific permissions.
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
)

# Used only to verify AppSail-to-Data-Store connectivity.
api_router.include_router(
    catalyst_status.router,
    prefix="/catalyst-status",
    tags=["catalyst"],
)