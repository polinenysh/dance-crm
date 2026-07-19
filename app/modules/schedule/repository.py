from datetime import datetime, time

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.groups.model import Group
from app.modules.schedule.model import Lesson, ScheduleSlot
from app.shared.enums import LessonStatus


class ScheduleRepository:
    """Репозиторий расписания и конкретных занятий."""

    @staticmethod
    def slot_options() -> tuple:
        """Возвращает настройки загрузки связей шаблона."""

        return (
            selectinload(ScheduleSlot.group),
            selectinload(ScheduleSlot.hall),
        )

    @staticmethod
    def lesson_options() -> tuple:
        """Возвращает настройки загрузки связей занятия."""

        return (
            selectinload(Lesson.group),
            selectinload(Lesson.hall),
            selectinload(Lesson.teacher),
        )

    async def get_slots(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
        group_id: int | None = None,
        hall_id: int | None = None,
        active_only: bool = False,
    ) -> list[ScheduleSlot]:
        """Возвращает шаблоны расписания с фильтрацией."""

        query: Select[tuple[ScheduleSlot]] = select(ScheduleSlot).join(ScheduleSlot.group).options(*self.slot_options())

        if branch_id is not None:
            query = query.where(Group.branch_id == branch_id)

        if group_id is not None:
            query = query.where(ScheduleSlot.group_id == group_id)

        if hall_id is not None:
            query = query.where(ScheduleSlot.hall_id == hall_id)

        if active_only:
            query = query.where(ScheduleSlot.is_active.is_(True))

        query = query.order_by(
            ScheduleSlot.weekday,
            ScheduleSlot.start_time,
        )

        result = await session.scalars(query)
        return list(result.unique().all())

    async def get_slot_by_id(
        self,
        session: AsyncSession,
        slot_id: int,
    ) -> ScheduleSlot | None:
        """Возвращает шаблон расписания по идентификатору."""

        result = await session.scalars(
            select(ScheduleSlot)
            .options(*self.slot_options())
            .where(ScheduleSlot.id == slot_id)
            .execution_options(populate_existing=True)
        )

        return result.first()

    async def find_slot_conflict(
        self,
        session: AsyncSession,
        weekday: int,
        start_time: time,
        end_time: time,
        hall_id: int | None = None,
        group_id: int | None = None,
        teacher_id: int | None = None,
        excluded_slot_id: int | None = None,
    ) -> ScheduleSlot | None:
        """Ищет пересечение повторяющегося расписания."""

        query = (
            select(ScheduleSlot)
            .join(ScheduleSlot.group)
            .where(
                ScheduleSlot.weekday == weekday,
                ScheduleSlot.is_active.is_(True),
                ScheduleSlot.start_time < end_time,
                ScheduleSlot.end_time > start_time,
            )
        )

        conflict_conditions = []

        if hall_id is not None:
            conflict_conditions.append(ScheduleSlot.hall_id == hall_id)

        if group_id is not None:
            conflict_conditions.append(ScheduleSlot.group_id == group_id)

        if teacher_id is not None:
            conflict_conditions.append(Group.teacher_id == teacher_id)

        query = query.where(or_(*conflict_conditions))

        if excluded_slot_id is not None:
            query = query.where(ScheduleSlot.id != excluded_slot_id)

        result = await session.scalars(query.limit(1))
        return result.first()

    async def get_lesson_by_slot_and_start(
        self,
        session: AsyncSession,
        slot_id: int,
        starts_at: datetime,
    ) -> Lesson | None:
        """Возвращает занятие шаблона по времени начала."""

        result = await session.scalars(
            select(Lesson).where(
                Lesson.schedule_slot_id == slot_id,
                Lesson.starts_at == starts_at,
            )
        )

        return result.first()

    async def get_lessons(
        self,
        session: AsyncSession,
        date_from: datetime,
        date_to: datetime,
        branch_id: int | None = None,
        group_id: int | None = None,
        teacher_id: int | None = None,
        hall_id: int | None = None,
        lesson_status: LessonStatus | None = None,
    ) -> list[Lesson]:
        """Возвращает конкретные занятия с фильтрацией."""

        query: Select[tuple[Lesson]] = (
            select(Lesson)
            .join(Lesson.group)
            .options(*self.lesson_options())
            .where(
                Lesson.starts_at >= date_from,
                Lesson.starts_at < date_to,
            )
        )

        if branch_id is not None:
            query = query.where(Group.branch_id == branch_id)

        if group_id is not None:
            query = query.where(Lesson.group_id == group_id)

        if teacher_id is not None:
            query = query.where(Lesson.teacher_id == teacher_id)

        if hall_id is not None:
            query = query.where(Lesson.hall_id == hall_id)

        if lesson_status is not None:
            query = query.where(Lesson.status == lesson_status)

        query = query.order_by(Lesson.starts_at)

        result = await session.scalars(query)
        return list(result.unique().all())

    async def get_lesson_by_id(
        self,
        session: AsyncSession,
        lesson_id: int,
    ) -> Lesson | None:
        """Возвращает занятие по идентификатору."""

        result = await session.scalars(
            select(Lesson)
            .options(*self.lesson_options())
            .where(Lesson.id == lesson_id)
            .execution_options(populate_existing=True)
        )

        return result.first()

    async def find_lesson_conflict(
        self,
        session: AsyncSession,
        starts_at: datetime,
        ends_at: datetime,
        hall_id: int,
        teacher_id: int,
        group_id: int,
        excluded_lesson_id: int | None = None,
    ) -> Lesson | None:
        """Ищет пересечение конкретных занятий."""

        query = select(Lesson).where(
            Lesson.status != LessonStatus.CANCELLED,
            Lesson.starts_at < ends_at,
            Lesson.ends_at > starts_at,
            or_(
                Lesson.hall_id == hall_id,
                Lesson.teacher_id == teacher_id,
                Lesson.group_id == group_id,
            ),
        )

        if excluded_lesson_id is not None:
            query = query.where(Lesson.id != excluded_lesson_id)

        result = await session.scalars(query.limit(1))
        return result.first()


schedule_repository = ScheduleRepository()
