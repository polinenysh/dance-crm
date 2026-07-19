from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep
from app.modules.students.schemas import (
    StudentArchiveRequest,
    StudentCreate,
    StudentResponse,
    StudentUpdate,
)
from app.modules.students.service import student_service
from app.shared.enums import StudentStatus

router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


@router.get(
    "",
    response_model=list[StudentResponse],
)
async def get_students(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    branch_id: int | None = Query(default=None, gt=0),
    parent_id: int | None = Query(default=None, gt=0),
    student_status: StudentStatus | None = Query(
        default=None,
        alias="status",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
    ),
) -> list[StudentResponse]:
    """Возвращает список учеников."""

    return await student_service.get_all(
        session=session,
        current_user=current_user,
        branch_id=branch_id,
        parent_id=parent_id,
        student_status=student_status,
        search=search,
    )


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student(
    data: StudentCreate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentResponse:
    """Создаёт карточку ученика."""

    return await student_service.create(
        session,
        data,
        current_user,
    )


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
async def get_student(
    student_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentResponse:
    """Возвращает ученика по идентификатору."""

    return await student_service.get_by_id(
        session,
        student_id,
        current_user,
    )


@router.patch(
    "/{student_id}",
    response_model=StudentResponse,
)
async def update_student(
    student_id: int,
    data: StudentUpdate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentResponse:
    """Обновляет карточку ученика."""

    return await student_service.update(
        session,
        student_id,
        data,
        current_user,
    )


@router.post(
    "/{student_id}/archive",
    response_model=StudentResponse,
)
async def archive_student(
    student_id: int,
    data: StudentArchiveRequest,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentResponse:
    """Переводит ученика в архив."""

    return await student_service.archive(
        session,
        student_id,
        current_user,
        data.comment,
    )
