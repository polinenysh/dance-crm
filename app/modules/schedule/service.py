from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import ensure_branch_access
from app.modules.groups.repository import group_repository
from app.modules.halls.repository import hall_repository
from app.modules.schedule.model import Lesson, ScheduleSlot
from app.modules.schedule.repository import schedule_repository
from app.modules.schedule.schemas import (
    LessonCancelRequest,
    LessonGenerateRequest,
    ScheduleSlotCreate,
    ScheduleSlotUpdate,
)
from app.modules.users.model import User
from app.modules.subscriptions.service import (
    student_subscription_service,
)
from app.shared.enums import LessonStatus, UserRole

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")


class ScheduleService:
    """Сервис бизнес-логики расписания."""

    async def get_slots(
        self,
        session: AsyncSession,
        current_user: User,
        branch_id: int | None = None,
        group_id: int | None = None,
        hall_id: int | None = None,
        active_only: bool = False,
    ) -> list[ScheduleSlot]:
        """Возвращает доступные шаблоны расписания."""

        if current_user.role == UserRole.BRANCH_ADMIN:
            branch_id = current_user.branch_id

        return await schedule_repository.get_slots(
            session=session,
            branch_id=branch_id,
            group_id=group_id,
            hall_id=hall_id,
            active_only=active_only,
        )

    async def get_slot(
        self,
        session: AsyncSession,
        slot_id: int,
        current_user: User,
    ) -> ScheduleSlot:
        """Возвращает шаблон с проверкой доступа."""

        slot = await schedule_repository.get_slot_by_id(
            session,
            slot_id,
        )

        if slot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Элемент расписания не найден",
            )

        ensure_branch_access(
            current_user,
            slot.group.branch_id,
        )

        return slot

    async def validate_slot_relations(
        self,
        session: AsyncSession,
        group_id: int,
        hall_id: int,
    ) -> tuple:
        """Проверяет группу и зал шаблона."""

        group = await group_repository.get_by_id(
            session,
            group_id,
        )

        if group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )

        hall = await hall_repository.get_by_id(
            session,
            hall_id,
        )

        if hall is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Зал не найден",
            )

        if not group.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя создать расписание для неактивной группы",
            )

        if not hall.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя использовать неактивный зал",
            )

        if hall.branch_id != group.branch_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Группа и зал относятся к разным филиалам",
            )

        if group.max_students > hall.capacity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Вместимость зала меньше вместимости группы",
            )

        return group, hall

    async def ensure_no_slot_conflict(
        self,
        session: AsyncSession,
        group_id: int,
        hall_id: int,
        teacher_id: int,
        weekday: int,
        start_time: time,
        end_time: time,
        excluded_slot_id: int | None = None,
    ) -> None:
        """Проверяет отсутствие пересечений расписания."""

        conflict = await schedule_repository.find_slot_conflict(
            session=session,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            hall_id=hall_id,
            group_id=group_id,
            teacher_id=teacher_id,
            excluded_slot_id=excluded_slot_id,
        )

        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Расписание пересекается по группе, залу "
                    "или преподавателю"
                ),
            )

    async def create_slot(
        self,
        session: AsyncSession,
        data: ScheduleSlotCreate,
        current_user: User,
    ) -> ScheduleSlot:
        """Создаёт повторяющийся элемент расписания."""

        group, _ = await self.validate_slot_relations(
            session,
            data.group_id,
            data.hall_id,
        )

        ensure_branch_access(
            current_user,
            group.branch_id,
        )

        await self.ensure_no_slot_conflict(
            session=session,
            group_id=group.id,
            hall_id=data.hall_id,
            teacher_id=group.teacher_id,
            weekday=int(data.weekday),
            start_time=data.start_time,
            end_time=data.end_time,
        )

        slot = ScheduleSlot(
            **data.model_dump(),
            is_active=True,
        )

        session.add(slot)
        await session.commit()

        created_slot = await schedule_repository.get_slot_by_id(
            session,
            slot.id,
        )

        if created_slot is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить созданное расписание",
            )

        return created_slot

    async def update_slot(
        self,
        session: AsyncSession,
        slot_id: int,
        data: ScheduleSlotUpdate,
        current_user: User,
    ) -> ScheduleSlot:
        """Обновляет повторяющийся элемент расписания."""

        slot = await self.get_slot(
            session,
            slot_id,
            current_user,
        )

        target_hall_id = data.hall_id or slot.hall_id
        target_weekday = (
            int(data.weekday)
            if data.weekday is not None
            else int(slot.weekday)
        )
        target_start = data.start_time or slot.start_time
        target_end = data.end_time or slot.end_time

        if target_start >= target_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Время окончания должно быть позже начала",
            )

        group, _ = await self.validate_slot_relations(
            session,
            slot.group_id,
            target_hall_id,
        )

        await self.ensure_no_slot_conflict(
            session=session,
            group_id=group.id,
            hall_id=target_hall_id,
            teacher_id=group.teacher_id,
            weekday=target_weekday,
            start_time=target_start,
            end_time=target_end,
            excluded_slot_id=slot.id,
        )

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(slot, field, value)

        await session.commit()

        updated_slot = await schedule_repository.get_slot_by_id(
            session,
            slot.id,
        )

        if updated_slot is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновлённое расписание",
            )

        return updated_slot

    async def generate_lessons(
        self,
        session: AsyncSession,
        slot_id: int,
        data: LessonGenerateRequest,
        current_user: User,
    ) -> list[Lesson]:
        """Создаёт конкретные занятия по шаблону."""

        slot = await self.get_slot(
            session,
            slot_id,
            current_user,
        )

        if not slot.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя создавать занятия по неактивному расписанию",
            )

        current_date = data.date_from
        created_lessons: list[Lesson] = []

        while current_date <= data.date_to:
            if current_date.weekday() == int(slot.weekday):
                starts_at = datetime.combine(
                    current_date,
                    slot.start_time,
                    tzinfo=MOSCOW_TIMEZONE,
                )
                ends_at = datetime.combine(
                    current_date,
                    slot.end_time,
                    tzinfo=MOSCOW_TIMEZONE,
                )

                existing_lesson = (
                    await schedule_repository.get_lesson_by_slot_and_start(
                        session,
                        slot.id,
                        starts_at,
                    )
                )

                if existing_lesson is None:
                    conflict = await schedule_repository.find_lesson_conflict(
                        session=session,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        hall_id=slot.hall_id,
                        teacher_id=slot.group.teacher_id,
                        group_id=slot.group_id,
                    )

                    if conflict is None:
                        lesson = Lesson(
                            schedule_slot_id=slot.id,
                            group_id=slot.group_id,
                            hall_id=slot.hall_id,
                            teacher_id=slot.group.teacher_id,
                            starts_at=starts_at,
                            ends_at=ends_at,
                            status=LessonStatus.PLANNED,
                            cancellation_reason=None,
                            cancelled_by_studio=False,
                            cancelled_by=None,
                        )

                        session.add(lesson)
                        created_lessons.append(lesson)

            current_date += timedelta(days=1)

        await session.commit()

        result: list[Lesson] = []

        for lesson in created_lessons:
            loaded_lesson = await schedule_repository.get_lesson_by_id(
                session,
                lesson.id,
            )

            if loaded_lesson is not None:
                result.append(loaded_lesson)

        return result

    async def get_lesson(
        self,
        session: AsyncSession,
        lesson_id: int,
        current_user: User,
    ) -> Lesson:
        """Возвращает занятие с проверкой доступа."""

        lesson = await schedule_repository.get_lesson_by_id(
            session,
            lesson_id,
        )

        if lesson is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Занятие не найдено",
            )

        ensure_branch_access(
            current_user,
            lesson.group.branch_id,
        )

        return lesson

    async def cancel_lesson(
        self,
        session: AsyncSession,
        lesson_id: int,
        data: LessonCancelRequest,
        current_user: User,
    ) -> Lesson:
        """Отменяет занятие и при необходимости продлевает абонементы."""

        lesson = await self.get_lesson(
            session,
            lesson_id,
            current_user,
        )

        if lesson.status == LessonStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя отменить завершённое занятие",
            )

        if lesson.status == LessonStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Занятие уже отменено",
            )

        lesson.status = LessonStatus.CANCELLED
        lesson.cancellation_reason = data.reason
        lesson.cancelled_by_studio = data.cancelled_by_studio
        lesson.cancelled_by = current_user.id

        if data.cancelled_by_studio:
            await student_subscription_service.extend_for_cancelled_lesson(
                session=session,
                lesson=lesson,
                current_user=current_user,
            )

        await session.commit()

        updated_lesson = await schedule_repository.get_lesson_by_id(
            session,
            lesson.id,
        )

        if updated_lesson is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить отменённое занятие",
            )

        return updated_lesson


schedule_service = ScheduleService()