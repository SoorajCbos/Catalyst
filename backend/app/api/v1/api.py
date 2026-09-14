from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    health,
    organizations,
    templates,
    users,
)

api_router = APIRouter()

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

api_router.include_router(
    organizations.router,
    prefix="/organizations",
    tags=["organizations"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
)

api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["templates"],
)