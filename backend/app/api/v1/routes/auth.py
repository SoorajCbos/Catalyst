from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.user_store import authenticate_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    recordId: str
    username: str
    email: str
    organizationId: str
    active: bool
    profile: str


class LoginResponse(BaseModel):
    user: UserResponse
    entryPoint: str


ENTRY_POINTS = {
    "platform_admin": "/platform-admin",
    "organization_admin": "/organization-admin",
    "member": "/app",
}


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password)

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