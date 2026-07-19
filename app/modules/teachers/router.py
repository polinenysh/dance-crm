from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import CurrentUserDep, OwnerDep
from app.modules.teachers.schemas import (
    TeacherCreate,
    TeacherResponse,
    TeacherUpdate,
)
from app.modules.teachers.service import teacher_service

router = APIRouter(
    prefix="/teachers",
    tags=["Teachers"],
)


@router.get(
    "",
    response_model=list[TeacherResponse],
)
async def get_teachers(
    session: SessionDep,
    _: CurrentUserDep,
    dance_style_id: int | None = Query(
        default=None,
        gt=0,
    ),
    active_only: bool = Query(default=False),
    search: str | None = Query(
        default=None,
        min_length=1,
    ),
) -> list[TeacherResponse]:
    """Возвращает список преподавателей."""

    return await teacher_service.get_all(
        session=session,
        dance_style_id=dance_style_id,
        active_only=active_only,
        search=search,
    )


@router.post(
    "",
    response_model=TeacherResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_teacher(
    data: TeacherCreate,
    session: SessionDep,
    _: OwnerDep,
) -> TeacherResponse:
    """Создаёт профиль преподавателя."""

    return await teacher_service.create(
        session,
        data,
    )


@router.get(
    "/{teacher_id}",
    response_model=TeacherResponse,
)
async def get_teacher(
    teacher_id: int,
    session: SessionDep,
    _: CurrentUserDep,
) -> TeacherResponse:
    """Возвращает преподавателя по идентификатору."""

    return await teacher_service.get_by_id(
        session,
        teacher_id,
    )


@router.patch(
    "/{teacher_id}",
    response_model=TeacherResponse,
)
async def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    session: SessionDep,
    _: OwnerDep,
) -> TeacherResponse:
    """Обновляет профиль преподавателя."""

    return await teacher_service.update(
        session,
        teacher_id,
        data,
    )
