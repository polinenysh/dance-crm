from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.attendance.model import Attendance
from app.modules.subscriptions.model import StudentSubscription


class AttendanceRepository:
    """Репозиторий для работы с посещаемостью."""

    @staticmethod
    def related_options() -> tuple:
        """Возвращает настройки загрузки связанных данных."""
        return (
            selectinload(Attendance.student),
            selectinload(Attendance.subscription).selectinload(StudentSubscription.plan),
        )

    async def get_by_lesson(self, session: AsyncSession, lesson_id: int) -> list[Attendance]:
        """Возвращает посещаемость конкретного занятия."""
        result = await session.scalars(
            select(Attendance)
            .options(*self.related_options())
            .where(Attendance.lesson_id == lesson_id)
            .order_by(Attendance.student_id)
            .execution_options(populate_existing=True)
        )
        return list(result.unique().all())

    async def get_valid_subscription(
        self, session: AsyncSession, student_id: int, branch_id: int, lesson_date: date
    ) -> StudentSubscription | None:
        """Блокирует и возвращает первый абонемент со свободным занятием."""
        subscriptions = await session.scalars(
            select(StudentSubscription)
            .where(
                StudentSubscription.student_id == student_id,
                StudentSubscription.branch_id == branch_id,
                StudentSubscription.starts_on <= lesson_date,
                StudentSubscription.expires_on >= lesson_date,
            )
            .order_by(StudentSubscription.starts_on, StudentSubscription.id)
            .with_for_update()
        )
        for subscription in subscriptions.all():
            used = await session.scalar(
                select(func.count(Attendance.id)).where(Attendance.subscription_id == subscription.id)
            )
            if (used or 0) < subscription.lessons_count:
                return subscription
        return None


attendance_repository = AttendanceRepository()
