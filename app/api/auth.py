from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResendActivationRequest,
    ResetPasswordRequest,
    TokenPairResponse,
)
from app.services.auth import AuthService, build_auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return build_auth_service(session)


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.register(data)


@router.get("/activate", response_model=MessageResponse)
async def activate(
    token: Annotated[str, Query(min_length=1)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.activate(token)


@router.post("/activation/resend", response_model=MessageResponse)
async def resend_activation(
    data: ResendActivationRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.resend_activation(data)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    data: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    return await service.login(data)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    data: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    return await service.refresh(data)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    data: LogoutRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.logout(data)


@router.get("/me")
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    return {"email": current_user.email}


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.change_password(current_user, data)


@router.post("/password/forgot", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.forgot_password(data)


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.reset_password(data)
