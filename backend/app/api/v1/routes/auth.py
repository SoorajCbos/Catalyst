"""Authentication and password-management routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.user_store import (
    authenticate_user,
    change_user_password,
)

router = APIRouter()


class LoginRequest(BaseModel):
    """Username and password sent by the login form."""

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


class LoginResponse(BaseModel):
    """Login result containing the user and their entry page."""

    user: UserResponse
    entryPoint: str


class ChangePasswordRequest(BaseModel):
    """Data required to replace a user's existing password."""

    username: str = Field(min_length=1, max_length=100)
    currentPassword: str = Field(min_length=1)
    newPassword: str = Field(min_length=8)
    confirmPassword: str = Field(min_length=8)


class MessageResponse(BaseModel):
    """Simple success message returned after changing a password."""

    message: str


ENTRY_POINTS = {
    "platform_admin": "/platform-admin",
    "organization_admin": "/organization-admin",
    "member": "/app",
}


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    """Authenticate a user and return their correct entry point."""

    user = authenticate_user(payload.username.strip(), payload.password)

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

    return LoginResponse(
        user=UserResponse(**user),
        entryPoint=ENTRY_POINTS[user["profile"]],
    )


@router.post(
    "/change-password",
    response_model=MessageResponse,
)
def change_password(payload: ChangePasswordRequest) -> MessageResponse:
    """Validate the current password and replace it with a new password."""

    username = payload.username.strip()

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
        username=username,
        current_password=payload.currentPassword,
        new_password=payload.newPassword,
    )

    if not password_changed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or current password.",
        )

    return MessageResponse(message="Password changed successfully.")