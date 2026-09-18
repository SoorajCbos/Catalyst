"""Protected routes for listing and creating users."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.access import require_admin
from app.core.catalyst_app import get_catalyst_app
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
    """User information safe for administrators."""

    recordId: str
    username: str
    email: str
    organizationId: str
    active: bool
    profile: str
    mustChangePassword: bool


class CreatedUserResponse(UserResponse):
    """New user with their one-time default password."""

    defaultPassword: str


class CreateUserRequest(BaseModel):
    """Data accepted from the user form."""

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
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> list[UserResponse]:
    """List users within the administrator's allowed scope."""

    if current_user["profile"] == "organization_admin":
        if (
            organization_id
            and organization_id != current_user["organizationId"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view another organization's users.",
            )

        organization_id = current_user["organizationId"]

    return [
        UserResponse(**user)
        for user in list_users(
            organization_id=organization_id,
            catalyst_app=catalyst_app,
        )
    ]


@router.post(
    "",
    response_model=CreatedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_user(
    payload: CreateUserRequest,
    current_user: dict[str, Any] = Depends(require_admin),
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> CreatedUserResponse:
    """Create a user while enforcing role and member limits."""

    username = payload.username.strip()
    email = payload.email.strip()

    if current_user["profile"] == "organization_admin":
        if payload.organizationId != current_user["organizationId"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add users to your organization.",
            )

        if payload.profile != "member":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization administrators can only add members.",
            )

    if username_exists(username, catalyst_app):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already in use.",
        )

    organization = get_organization(
        payload.organizationId,
        catalyst_app,
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    current_count = count_organization_users(
        payload.organizationId,
        catalyst_app,
    )

    if current_count >= organization["memberLimit"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The organization has reached its member limit.",
        )

    user = create_user(
        username=username,
        email=email,
        organization_id=payload.organizationId,
        profile=payload.profile,
        catalyst_app=catalyst_app,
    )

    return CreatedUserResponse(**user)