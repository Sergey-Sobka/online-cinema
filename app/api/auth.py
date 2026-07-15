from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
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
    summary="Register user",
    description=(
        "Create an inactive user account and send a 24-hour activation link "
        "to the provided email address."
    ),
    response_description="Registration accepted and activation email sent.",
)
async def register(
    data: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.register(data)


@router.get(
    "/activate",
    response_model=MessageResponse,
    summary="Activate account",
    description="Activate an inactive account using the token from the email link.",
    response_description="Account activated successfully.",
)
async def activate(
    token: Annotated[
        str,
        Query(
            min_length=1,
            description="Activation token received by email.",
            examples=["a91BrvM7EoV0sXbW"],
        ),
    ],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.activate(token)


@router.post(
    "/activation/resend",
    response_model=MessageResponse,
    summary="Resend activation email",
    description=(
        "Send a new activation link for an inactive account. "
        "The new link is valid for 24 hours."
    ),
    response_description="Activation email has been sent.",
)
async def resend_activation(
    data: ResendActivationRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.resend_activation(data)


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Login with JSON body",
    description=(
        "Authenticate an active user with email and password. "
        "Use this endpoint for JSON API clients."
    ),
    response_description="Access and refresh tokens returned.",
)
async def login(
    data: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    return await service.login(data)


@router.post(
    "/token",
    response_model=TokenPairResponse,
    summary="Swagger OAuth2 login",
    description=(
        "OAuth2 password-flow endpoint used by Swagger Authorize. "
        "Use the email address as username and leave client credentials empty."
    ),
    response_description="Access and refresh tokens returned.",
)
async def token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    try:
        login_data = LoginRequest(
            email=form_data.username,
            password=form_data.password,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    return await service.login(login_data)


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Refresh access token",
    description="Use a valid refresh token to receive a new token pair.",
    response_description="New access and refresh tokens returned.",
)
async def refresh(
    data: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    return await service.refresh(data)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Delete the provided refresh token so it cannot be used again.",
    response_description="Refresh token revoked.",
)
async def logout(
    data: LogoutRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.logout(data)


@router.get(
    "/me",
    summary="Get current user",
    description="Return basic information about the authenticated active user.",
    response_description="Authenticated user returned.",
)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    return {"email": current_user.email}


@router.post(
    "/password/change",
    response_model=MessageResponse,
    summary="Change password",
    description=(
        "Change the password for the authenticated user after confirming "
        "the current password. Existing refresh tokens are revoked."
    ),
    response_description="Password changed successfully.",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.change_password(current_user, data)


@router.post(
    "/password/forgot",
    response_model=MessageResponse,
    summary="Request password reset",
    description=(
        "Generate a password reset token for an active account and send "
        "reset instructions by email."
    ),
    response_description="Password reset instructions accepted.",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.forgot_password(data)


@router.post(
    "/password/reset",
    response_model=MessageResponse,
    summary="Reset password",
    description=(
        "Set a new password using a valid password reset token. "
        "Existing refresh tokens are revoked."
    ),
    response_description="Password reset successfully.",
)
async def reset_password(
    data: ResetPasswordRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    return await service.reset_password(data)
