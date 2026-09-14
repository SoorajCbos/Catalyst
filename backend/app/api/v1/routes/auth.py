"""Authentication and password-management routes."""

import os
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from pydantic import BaseModel, Field

from app.core.access import require_user
from app.core.jwt_auth import (
    JWT_EXPIRY_HOURS,
    SESSION_COOKIE_NAME,
    create_access_token,
)
from app.services.user_store import (
    authenticate_user,
    change_user_password,
)

router = APIRouter()


class LoginRequest(BaseModel):
    """Username and password submitted by the login page."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Authenticated user details returned to the frontend."""

    recordId: str
    username: str
    email: str
    organizationId: str
    active: bool
    profile: str
    mustChangePassword: bool


class LoginResponse(BaseModel):
    """Login response containing the user and their entry page."""

    user: UserResponse
    entryPoint: str


class ChangePasswordRequest(BaseModel):
    """
    Information required to replace the current user's password.

    Username is deliberately omitted. The backend gets the identity from
    the verified JWT instead of trusting a username sent by the browser.
    """

    currentPassword: str = Field(min_length=1)
    newPassword: str = Field(min_length=8)
    confirmPassword: str = Field(min_length=8)


class MessageResponse(BaseModel):
    """A simple API success message."""

    message: str


ENTRY_POINTS = {
    "platform_admin": "/platform-admin",
    "organization_admin": "/organization-admin",
    "member": "/app",
}


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
) -> LoginResponse:
    """Authenticate the user and create an HTTP-only JWT session."""

    user = authenticate_user(
        payload.username.strip(),
        payload.password,
    )

    # Use one generic error so callers cannot discover valid usernames.
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not user["active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive.",
        )

    token = create_access_token(user)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        # Local HTTP testing cannot use secure cookies. AppSail must set
        # APP_ENV=production so production cookies become HTTPS-only.
        secure=os.environ.get("APP_ENV") == "production",
        max_age=JWT_EXPIRY_HOURS * 60 * 60,
        path="/",
    )

    # New users with generated passwords must change them before entering
    # their normal organization area.
    entry_point = (
        "/change-password"
        if user["mustChangePassword"]
        else ENTRY_POINTS[user["profile"]]
    )

    return LoginResponse(
        user=UserResponse(**user),
        entryPoint=entry_point,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    current_user: dict[str, Any] = Depends(require_user),
) -> UserResponse:
    """Return the current active user from their verified JWT session."""

    return UserResponse(**current_user)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    """Remove the authentication cookie from the browser."""

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )

    return MessageResponse(message="Logged out successfully.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict[str, Any] = Depends(require_user),
) -> MessageResponse:
    """
    Change the password belonging to the authenticated user.

    The username comes from the verified session rather than the request,
    preventing one user from attempting to change another user's password.
    """

    if payload.newPassword != payload.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match.",
        )

    if payload.currentPassword == payload.newPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new password must be different from the current password.",
        )

    password_changed = change_user_password(
        username=current_user["username"],
        current_password=payload.currentPassword,
        new_password=payload.newPassword,
    )

    if not password_changed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    return MessageResponse(message="Password changed successfully.")