from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import MessageResponse, RegisterRequest, ResendActivationRequest
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
