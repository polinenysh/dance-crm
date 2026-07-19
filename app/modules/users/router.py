from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import OwnerDep
from app.modules.users.schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.modules.users.service import user_service

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=list[UserResponse],
)
async def get_users(
    session: SessionDep,
    _: OwnerDep,
    branch_id: int | None = Query(default=None, gt=0),
) -> list[UserResponse]:
    """Возвращает список сотрудников."""

    return await user_service.get_all(
        session,
        branch_id,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: UserCreate,
    session: SessionDep,
    _: OwnerDep,
) -> UserResponse:
    """Создаёт учётную запись сотрудника."""

    return await user_service.create(
        session,
        data,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    session: SessionDep,
    _: OwnerDep,
) -> UserResponse:
    """Возвращает сотрудника по идентификатору."""

    return await user_service.get_by_id(
        session,
        user_id,
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
async def update_user(
    user_id: int,
    data: UserUpdate,
    session: SessionDep,
    _: OwnerDep,
) -> UserResponse:
    """Обновляет данные сотрудника."""

    return await user_service.update(
        session,
        user_id,
        data,
    )
