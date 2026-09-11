"""API routes for listing and creating organizations."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

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
    """Organization data accepted from the create form."""

    name: str = Field(min_length=1, max_length=100)
    tier: str = Field(min_length=1, max_length=50)
    memberLimit: int = Field(ge=1)


@router.get("", response_model=list[OrganizationResponse])
def get_organizations() -> list[OrganizationResponse]:
    """Return all organizations."""

    return [
        OrganizationResponse(**organization)
        for organization in list_organizations()
    ]


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_organization(
    payload: CreateOrganizationRequest,
) -> OrganizationResponse:
    """Create and return a new organization."""

    name = payload.name.strip()
    tier = payload.tier.strip()

    if organization_name_exists(name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with that name already exists.",
        )

    organization = create_organization(
        name=name,
        tier=tier,
        member_limit=payload.memberLimit,
    )

    return OrganizationResponse(**organization)