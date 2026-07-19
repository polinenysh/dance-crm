from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep
from app.modules.schedule.schemas import (
    LessonCancelRequest,
    LessonGenerateRequest,
    LessonResponse,
    ScheduleSlotCreate,
    ScheduleSlotResponse,
    ScheduleSlotUpdate,
)
from app.modules.schedule.service import schedule_service
from app.shared.enums import LessonStatus
from app.modules.schedule.repository import schedule_repository

router = APIRouter(
    prefix="/schedule",
    tags=["Schedule"],
)

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")


@router.get(
    "/slots",
    response_model=list[ScheduleSlotResponse],
)
async def get_schedule_slots(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    branch_id: int | None = Query(default=None, gt=0),
    group_id: int | None = Query(default=None, gt=0),
    hall_id: int | None = Query(default=None, gt=0),
    active_only: bool = Query(default=False),
) -> list[ScheduleSlotResponse]:
    """Возвращает повторяющееся расписание."""

    return await schedule_service.get_slots(
        session=session,
        current_user=current_user,
        branch_id=branch_id,
        group_id=group_id,
        hall_id=hall_id,
        active_only=active_only,
    )


@router.post(
    "/slots",
    response_model=ScheduleSlotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule_slot(
    data: ScheduleSlotCreate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> ScheduleSlotResponse:
    """Создаёт повторяющийся элемент расписания."""

    return await schedule_service.create_slot(
        session,
        data,
        current_user,
    )


@router.patch(
    "/slots/{slot_id}",
    response_model=ScheduleSlotResponse,
)
async def update_schedule_slot(
    slot_id: int,
    data: ScheduleSlotUpdate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> ScheduleSlotResponse:
    """Обновляет повторяющееся расписание."""

    return await schedule_service.update_slot(
        session,
        slot_id,
        data,
        current_user,
    )


@router.post(
    "/slots/{slot_id}/lessons/generate",
    response_model=list[LessonResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_lessons(
    slot_id: int,
    data: LessonGenerateRequest,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> list[LessonResponse]:
    """Создаёт занятия по повторяющемуся расписанию."""

    return await schedule_service.generate_lessons(
        session,
        slot_id,
        data,
        current_user,
    )


@router.get(
    "/lessons",
    response_model=list[LessonResponse],
)
async def get_lessons(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    date_from: date,
    date_to: date,
    branch_id: int | None = Query(default=None, gt=0),
    group_id: int | None = Query(default=None, gt=0),
    teacher_id: int | None = Query(default=None, gt=0),
    hall_id: int | None = Query(default=None, gt=0),
    lesson_status: LessonStatus | None = Query(
        default=None,
        alias="status",
    ),
) -> list[LessonResponse]:
    """Возвращает конкретные занятия."""

    if date_from > date_to:
        return []

    if (date_to - date_from).days > 366:
        return []

    start_datetime = datetime.combine(
        date_from,
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )
    end_datetime = datetime.combine(
        date_to + timedelta(days=1),
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )

    if current_user.role.value == "branch_admin":
        branch_id = current_user.branch_id

    return await schedule_repository.get_lessons(
        session=session,
        date_from=start_datetime,
        date_to=end_datetime,
        branch_id=branch_id,
        group_id=group_id,
        teacher_id=teacher_id,
        hall_id=hall_id,
        lesson_status=lesson_status,
    )


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonResponse,
)
async def get_lesson(
    lesson_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> LessonResponse:
    """Возвращает конкретное занятие."""

    return await schedule_service.get_lesson(
        session,
        lesson_id,
        current_user,
    )


@router.post(
    "/lessons/{lesson_id}/cancel",
    response_model=LessonResponse,
)
async def cancel_lesson(
    lesson_id: int,
    data: LessonCancelRequest,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> LessonResponse:
    """Отменяет конкретное занятие."""

    return await schedule_service.cancel_lesson(
        session,
        lesson_id,
        data,
        current_user,
    )
