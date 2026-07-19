from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep
from app.modules.parents.schemas import (
    ParentCreate,
    ParentResponse,
    ParentUpdate,
)
from app.modules.parents.service import parent_service

router = APIRouter(
    prefix="/parents",
    tags=["Parents"],
)


@router.get(
    "",
    response_model=list[ParentResponse],
)
async def get_parents(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    search: str | None = Query(
        default=None,
        min_length=1,
    ),
) -> list[ParentResponse]:
    """Возвращает список родителей."""

    return await parent_service.get_all(
        session,
        current_user,
        search,
    )


@router.post(
    "",
    response_model=ParentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_parent(
    data: ParentCreate,
    session: SessionDep,
    _: AdminOrOwnerDep,
) -> ParentResponse:
    """Создаёт карточку родителя."""

    return await parent_service.create(
        session,
        data,
    )


@router.get(
    "/{parent_id}",
    response_model=ParentResponse,
)
async def get_parent(
    parent_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> ParentResponse:
    """Возвращает родителя по идентификатору."""

    return await parent_service.get_by_id(
        session,
        parent_id,
        current_user,
    )


@router.patch(
    "/{parent_id}",
    response_model=ParentResponse,
)
async def update_parent(
    parent_id: int,
    data: ParentUpdate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> ParentResponse:
    """Обновляет данные родителя."""

    return await parent_service.update(
        session,
        parent_id,
        data,
        current_user,
    )