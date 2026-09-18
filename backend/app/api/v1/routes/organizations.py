"""API routes for organization management."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.catalyst_app import get_catalyst_app
from app.services.organization_store import (
    create_organization,
    list_organizations,
    organization_name_exists,
)

router = APIRouter()


class OrganizationResponse(BaseModel):
    """Organization data returned to the frontend."""

    recordId: str
    name: str
    tier: str
    memberLimit: int


class CreateOrganizationRequest(BaseModel):
    """Organization data accepted from the form."""

    name: str = Field(min_length=1, max_length=100)
    tier: str = Field(min_length=1, max_length=50)
    memberLimit: int = Field(ge=1)


@router.get("", response_model=list[OrganizationResponse])
def get_organizations(
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> list[OrganizationResponse]:
    """List organizations using Catalyst or the local fallback."""

    return [
        OrganizationResponse(**organization)
        for organization in list_organizations(catalyst_app)
    ]


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_organization(
    payload: CreateOrganizationRequest,
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> OrganizationResponse:
    """Create an organization using the active storage system."""

    name = payload.name.strip()
    tier = payload.tier.strip()

    if organization_name_exists(name, catalyst_app):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with that name already exists.",
        )

    organization = create_organization(
        name=name,
        tier=tier,
        member_limit=payload.memberLimit,
        catalyst_app=catalyst_app,
    )

    return OrganizationResponse(**organization)