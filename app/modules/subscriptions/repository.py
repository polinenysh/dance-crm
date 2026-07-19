from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.subscriptions.model import (
    StudentSubscription,
    SubscriptionExtension,
)


class StudentSubscriptionRepository:
    """Репозиторий абонементов учеников."""

    @staticmethod
    def related_options() -> tuple:
        """Возвращает настройки загрузки связанных сущностей."""

        return (
            selectinload(StudentSubscription.student),
            selectinload(StudentSubscription.plan),
            selectinload(StudentSubscription.branch),
            selectinload(StudentSubscription.attendances),
            selectinload(StudentSubscription.extensions),
        )

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
        student_id: int | None = None,
        plan_id: int | None = None,
        active_on: date | None = None,
    ) -> list[StudentSubscription]:
        """Возвращает абонементы с фильтрацией."""

        query: Select[tuple[StudentSubscription]] = (
            select(StudentSubscription)
            .options(*self.related_options())
        )

        if branch_id is not None:
            query = query.where(
                StudentSubscription.branch_id == branch_id,
            )

        if student_id is not None:
            query = query.where(
                StudentSubscription.student_id == student_id,
            )

        if plan_id is not None:
            query = query.where(
                StudentSubscription.plan_id == plan_id,
            )

        if active_on is not None:
            query = query.where(
                StudentSubscription.starts_on <= active_on,
                StudentSubscription.expires_on >= active_on,
            )

        query = query.order_by(
            StudentSubscription.starts_on.desc(),
            StudentSubscription.id.desc(),
        )

        result = await session.scalars(query)

        return list(result.all())

    async def get_by_id(
        self,
        session: AsyncSession,
        subscription_id: int,
    ) -> StudentSubscription | None:
        """Возвращает абонемент по идентификатору."""

        result = await session.scalars(
            select(StudentSubscription)
            .options(*self.related_options())
            .where(
                StudentSubscription.id == subscription_id,
            )
            .execution_options(
                populate_existing=True,
            )
        )

        return result.first()

    async def find_overlapping(
        self,
        session: AsyncSession,
        student_id: int,
        starts_on: date,
        expires_on: date,
        excluded_subscription_id: int | None = None,
    ) -> StudentSubscription | None:
        """Ищет пересекающийся абонемент ученика."""

        query = select(StudentSubscription).where(
            StudentSubscription.student_id == student_id,
            StudentSubscription.starts_on <= expires_on,
            StudentSubscription.expires_on >= starts_on,
        )

        if excluded_subscription_id is not None:
            query = query.where(
                StudentSubscription.id != excluded_subscription_id,
            )

        result = await session.scalars(
            query.limit(1),
        )

        return result.first()
    
    async def get_valid_on_date(
        self,
        session: AsyncSession,
        student_id: int,
        branch_id: int,
        target_date: date,
    ) -> StudentSubscription | None:
        """Возвращает абонемент, действующий на указанную дату."""

        result = await session.scalars(
            select(StudentSubscription)
            .options(*self.related_options())
            .where(
                StudentSubscription.student_id == student_id,
                StudentSubscription.branch_id == branch_id,
                StudentSubscription.starts_on <= target_date,
                StudentSubscription.expires_on >= target_date,
            )
            .order_by(
                StudentSubscription.starts_on,
                StudentSubscription.id,
            )
            .limit(1)
        )

        return result.first()


    async def get_following_subscriptions(
        self,
        session: AsyncSession,
        student_id: int,
        after_date: date,
        excluded_subscription_id: int,
    ) -> list[StudentSubscription]:
        """Возвращает последующие абонементы ученика."""

        result = await session.scalars(
            select(StudentSubscription)
            .where(
                StudentSubscription.student_id == student_id,
                StudentSubscription.id != excluded_subscription_id,
                StudentSubscription.starts_on > after_date,
            )
            .order_by(
                StudentSubscription.starts_on,
                StudentSubscription.id,
            )
        )

        return list(result.all())


    async def get_extension_by_lesson(
        self,
        session: AsyncSession,
        subscription_id: int,
        lesson_id: int,
    ) -> SubscriptionExtension | None:
        """Возвращает продление, созданное из-за занятия."""

        result = await session.scalars(
            select(SubscriptionExtension).where(
                SubscriptionExtension.subscription_id == subscription_id,
                SubscriptionExtension.lesson_id == lesson_id,
            )
        )

        return result.first()


student_subscription_repository = StudentSubscriptionRepository()