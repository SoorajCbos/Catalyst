from fastapi import APIRouter, Depends

from app.api.v1.routes import (
    auth,
    health,
    organizations,
    templates,
    users,
)
from app.core.access import require_platform_admin

api_router = APIRouter()

# Health and authentication must remain public.
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

# Only platform administrators can manage organizations.
api_router.include_router(
    organizations.router,
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(require_platform_admin)],
)

# User routes perform their own platform-admin and organization-admin
# checks because each role has different organization permissions.
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
)

# Only platform administrators can manage reusable system templates.
api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["templates"],
    dependencies=[Depends(require_platform_admin)],
)