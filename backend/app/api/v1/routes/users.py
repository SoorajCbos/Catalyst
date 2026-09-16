"""Protected API routes for listing and creating users."""

import sqlite3
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.access import require_admin
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
    """User information safe to return to administrators."""

    recordId: str
    username: str
    email: str
    organizationId: str
    active: bool
    profile: str


class CreatedUserResponse(UserResponse):
    """New user response containing the one-time default password."""

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
    current_user: dict[str, Any] = Depends(require_admin),
) -> list[UserResponse]:
    """Return users according to the administrator's permissions."""

    if current_user["profile"] == "organization_admin":
        # Organization administrators can only view their own members.
        if (
            organization_id
            and organization_id != current_user["organizationId"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view users from another organization.",
            )

        organization_id = current_user["organizationId"]

    return [
        UserResponse(**user)
        for user in list_users(organization_id)
    ]


@router.post(
    "",
    response_model=CreatedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_user(
    payload: CreateUserRequest,
    current_user: dict[str, Any] = Depends(require_admin),
) -> CreatedUserResponse:
    """Create a user while enforcing organization and role boundaries."""

    username = payload.username.strip()
    email = payload.email.strip()

    if current_user["profile"] == "organization_admin":
        # Organization administrators cannot add users elsewhere.
        if payload.organizationId != current_user["organizationId"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add users to your own organization.",
            )

        # Organization administrators may create members, but they cannot
        # promote another user to administrator.
        if payload.profile != "member":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization administrators can only add members.",
            )

    # Usernames are the login identifier and must be unique globally.
    # Email addresses are contact data and are intentionally allowed to repeat.
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

    current_user_count = count_organization_users(
        payload.organizationId
    )

    # This backend check cannot be bypassed by manually calling the API.
    if current_user_count >= organization["memberLimit"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The organization has reached its member limit.",
        )

    try:
        user = create_user(
            username=username,
            email=email,
            organization_id=payload.organizationId,
            profile=payload.profile,
        )
    except sqlite3.IntegrityError as error:
        # The database UNIQUE constraint remains the final authority if two
        # requests pass username_exists() at the same time.
        if "users.username" in str(error) or "username" in str(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That username is already in use.",
            ) from error
        raise

    return CreatedUserResponse(**user)