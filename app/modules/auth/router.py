from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.db.session import SessionDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.modules.auth.service import auth_service
from app.modules.users.schemas import UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    session: SessionDep,
) -> TokenResponse:
    """Авторизует пользователя по email и паролю."""

    user = await auth_service.authenticate(
        session,
        form_data.username,
        form_data.password,
    )

    return auth_service.create_token_pair(user.id)


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
async def refresh_tokens(
    data: RefreshTokenRequest,
    session: SessionDep,
) -> TokenResponse:
    """Обновляет пару JWT-токенов."""

    return await auth_service.refresh_tokens(
        session,
        data.refresh_token,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Возвращает текущего пользователя."""

    return current_user


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> None:
    """Изменяет пароль текущего пользователя."""

    await auth_service.change_password(
        session,
        current_user,
        data.current_password,
        data.new_password,
    )
