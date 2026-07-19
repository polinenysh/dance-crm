from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep
from app.modules.groups.schemas import (
    GroupCreate,
    GroupMembershipCreate,
    GroupResponse,
    GroupUpdate,
)
from app.modules.groups.service import group_service

router = APIRouter(
    prefix="/groups",
    tags=["Groups"],
)


@router.get(
    "",
    response_model=list[GroupResponse],
)
async def get_groups(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    branch_id: int | None = Query(
        default=None,
        gt=0,
    ),
    teacher_id: int | None = Query(
        default=None,
        gt=0,
    ),
    dance_style_id: int | None = Query(
        default=None,
        gt=0,
    ),
    active_only: bool = Query(default=False),
    search: str | None = Query(
        default=None,
        min_length=1,
    ),
) -> list[GroupResponse]:
    """Возвращает список учебных групп."""

    return await group_service.get_all(
        session=session,
        current_user=current_user,
        branch_id=branch_id,
        teacher_id=teacher_id,
        dance_style_id=dance_style_id,
        active_only=active_only,
        search=search,
    )


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    data: GroupCreate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> GroupResponse:
    """Создаёт учебную группу."""

    return await group_service.create(
        session,
        data,
        current_user,
    )


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
)
async def get_group(
    group_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> GroupResponse:
    """Возвращает группу по идентификатору."""

    return await group_service.get_by_id(
        session,
        group_id,
        current_user,
    )


@router.patch(
    "/{group_id}",
    response_model=GroupResponse,
)
async def update_group(
    group_id: int,
    data: GroupUpdate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> GroupResponse:
    """Обновляет учебную группу."""

    return await group_service.update(
        session,
        group_id,
        data,
        current_user,
    )


@router.post(
    "/{group_id}/students",
    response_model=GroupResponse,
)
async def add_student_to_group(
    group_id: int,
    data: GroupMembershipCreate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> GroupResponse:
    """Добавляет ученика в состав группы."""

    return await group_service.add_student(
        session,
        group_id,
        data.student_id,
        current_user,
    )


@router.delete(
    "/{group_id}/students/{student_id}",
    response_model=GroupResponse,
)
async def remove_student_from_group(
    group_id: int,
    student_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> GroupResponse:
    """Исключает ученика из состава группы."""

    return await group_service.remove_student(
        session,
        group_id,
        student_id,
        current_user,
    )