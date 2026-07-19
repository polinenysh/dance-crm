import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.schemas import TokenResponse
from app.modules.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.users.model import User
from app.modules.users.repository import user_repository


class AuthService:
    """Сервис авторизации пользователей."""

    async def authenticate(
        self,
        session: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        """Проверяет email и пароль пользователя."""

        user = await user_repository.get_by_email(
            session,
            email,
        )

        if user is None or not verify_password(
            password,
            user.hashed_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учётная запись деактивирована",
            )

        return user

    def create_token_pair(
        self,
        user_id: int,
    ) -> TokenResponse:
        """Создаёт пару access- и refresh-токенов."""

        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )

    async def refresh_tokens(
        self,
        session: AsyncSession,
        refresh_token: str,
    ) -> TokenResponse:
        """Обновляет пару токенов по refresh-токену."""

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        )

        try:
            payload = decode_token(refresh_token)

            if payload.get("type") != "refresh":
                raise credentials_exception

            subject = payload.get("sub")

            if subject is None:
                raise credentials_exception

            user_id = int(subject)

        except (jwt.InvalidTokenError, ValueError):
            raise credentials_exception from None

        user = await user_repository.get_by_id(
            session,
            user_id,
        )

        if user is None or not user.is_active:
            raise credentials_exception

        return self.create_token_pair(user.id)

    async def change_password(
        self,
        session: AsyncSession,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """Изменяет пароль текущего пользователя."""

        if not verify_password(
            current_password,
            user.hashed_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Текущий пароль указан неверно",
            )

        user.hashed_password = hash_password(new_password)

        await session.commit()


auth_service = AuthService()