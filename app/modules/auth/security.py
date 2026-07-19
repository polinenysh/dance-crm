from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

TokenType = Literal["access", "refresh"]

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Создаёт безопасный хеш пароля."""

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Проверяет соответствие пароля сохранённому хешу."""

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    """Создаёт подписанный JWT-токен."""

    now = datetime.now(UTC)
    expires_at = now + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(user_id: int) -> str:
    """Создаёт access-токен пользователя."""

    return create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes,
        ),
    )


def create_refresh_token(user_id: int) -> str:
    """Создаёт refresh-токен пользователя."""

    return create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.refresh_token_expire_days,
        ),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Проверяет подпись JWT и возвращает его содержимое."""

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
