from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Схема ответа с JWT-токенами."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Схема обновления пары JWT-токенов."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Схема изменения пароля."""

    current_password: str
    new_password: str = Field(
        min_length=8,
        max_length=128,
    )
