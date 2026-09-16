from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.organization_guide_store import (
    create_organization_guide,
    get_organization_guide,
    list_organization_guides,
    update_organization_guide,
)
from app.services.organization_store import get_organization

router = APIRouter()


class OrganizationGuideResponse(BaseModel):
    recordId: str
    organizationId: str
    title: str
    guideType: str
    audience: str
    fileName: str
    filePath: str
    content: str
    createdAt: str
    updatedAt: str


class SaveOrganizationGuideRequest(BaseModel):
    organizationId: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=150)
    guideType: Literal["main", "profile", "role"]
    audience: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=100_000)


@router.get("", response_model=list[OrganizationGuideResponse])
def get_guides(
    organization_id: str | None = None,
) -> list[OrganizationGuideResponse]:
    return [
        OrganizationGuideResponse(**guide)
        for guide in list_organization_guides(organization_id)
    ]


@router.post(
    "",
    response_model=OrganizationGuideResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_guide(
    payload: SaveOrganizationGuideRequest,
) -> OrganizationGuideResponse:
    organization_id = payload.organizationId.strip()

    if get_organization(organization_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    guide = create_organization_guide(
        organization_id=organization_id,
        title=payload.title.strip(),
        guide_type=payload.guideType,
        audience=payload.audience.strip(),
        content=payload.content,
    )
    return OrganizationGuideResponse(**guide)


@router.put("/{record_id}", response_model=OrganizationGuideResponse)
def put_guide(
    record_id: str,
    payload: SaveOrganizationGuideRequest,
) -> OrganizationGuideResponse:
    organization_id = payload.organizationId.strip()

    if get_organization(organization_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    guide = update_organization_guide(
        record_id=record_id,
        organization_id=organization_id,
        title=payload.title.strip(),
        guide_type=payload.guideType,
        audience=payload.audience.strip(),
        content=payload.content,
    )

    if guide is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization guide not found.",
        )

    return OrganizationGuideResponse(**guide)