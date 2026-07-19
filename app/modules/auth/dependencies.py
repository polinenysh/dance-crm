from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.db.session import SessionDep
from app.modules.auth.security import decode_token
from app.modules.users.model import User
from app.modules.users.repository import user_repository
from app.shared.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)

TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(
    token: TokenDep,
    session: SessionDep,
) -> User:
    """Возвращает активного пользователя из access-токена."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить авторизацию",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)

        if payload.get("type") != "access":
            raise credentials_exception

        subject = payload.get("sub")

        if subject is None:
            raise credentials_exception

        user_id = int(subject)

    except jwt.InvalidTokenError, ValueError:
        raise credentials_exception from None

    user = await user_repository.get_by_id(
        session,
        user_id,
    )

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись деактивирована",
        )

    return user


CurrentUserDep = Annotated[
    User,
    Depends(get_current_user),
]


async def require_owner(
    current_user: CurrentUserDep,
) -> User:
    """Разрешает доступ только руководителю."""

    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    return current_user


OwnerDep = Annotated[
    User,
    Depends(require_owner),
]


async def require_admin_or_owner(
    current_user: CurrentUserDep,
) -> User:
    """Разрешает доступ руководителю и администратору."""

    allowed_roles = {
        UserRole.OWNER,
        UserRole.BRANCH_ADMIN,
    }

    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    return current_user


AdminOrOwnerDep = Annotated[
    User,
    Depends(require_admin_or_owner),
]


def ensure_branch_access(
    current_user: User,
    branch_id: int,
) -> None:
    """Проверяет доступ сотрудника к указанному филиалу."""

    if current_user.role == UserRole.OWNER:
        return

    if current_user.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому филиалу",
        )
