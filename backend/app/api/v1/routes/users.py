"""API routes for listing and creating users."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.organization_store import (
    count_organization_users,
    get_organization,
)
from app.services.user_store import (
    create_user,
    list_users,
    username_exists,
)

router = APIRouter()


class UserResponse(BaseModel):
    """User information that is safe to return to the frontend."""

    recordId: str
    username: str
    email: str
    organizationId: str
    active: bool
    profile: str


class CreatedUserResponse(UserResponse):
    """
    Response returned immediately after creating a user.

    The default password is shown once. It is not returned when users are
    listed because the plain password is never stored.
    """

    defaultPassword: str


class CreateUserRequest(BaseModel):
    """Data accepted from the Create User form."""

    username: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=255)
    organizationId: str = Field(min_length=1)
    profile: Literal["organization_admin", "member"]


@router.get("", response_model=list[UserResponse])
def get_users(
    organization_id: str | None = Query(
        default=None,
        alias="organizationId",
    ),
) -> list[UserResponse]:
    """
    Return users, optionally filtered by organization.

    The URL can be either:
        /api/v1/users
        /api/v1/users?organizationId=org_123
    """

    return [
        UserResponse(**user)
        for user in list_users(organization_id)
    ]


@router.post(
    "",
    response_model=CreatedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_user(payload: CreateUserRequest) -> CreatedUserResponse:
    """Create a user with a generated default password."""

    username = payload.username.strip()
    email = payload.email.strip()

    if username_exists(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already in use.",
        )

    organization = get_organization(payload.organizationId)

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    current_user_count = count_organization_users(payload.organizationId)

    # Stop creation when the organization has used all purchased seats.
    if current_user_count >= organization["memberLimit"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The organization has reached its member limit.",
        )

    user = create_user(
        username=username,
        email=email,
        organization_id=payload.organizationId,
        profile=payload.profile,
    )

    return CreatedUserResponse(**user)