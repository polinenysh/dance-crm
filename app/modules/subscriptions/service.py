from datetime import date, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import ensure_branch_access
from app.modules.groups.repository import group_repository
from app.modules.schedule.model import Lesson
from app.modules.students.repository import student_repository
from app.modules.subscription_plans.repository import (
    subscription_plan_repository,
)
from app.modules.subscriptions.model import (
    StudentSubscription,
    SubscriptionExtension,
)
from app.modules.subscriptions.repository import (
    student_subscription_repository,
)
from app.modules.subscriptions.schemas import (
    StudentSubscriptionCreate,
    StudentSubscriptionUpdate,
    SubscriptionExtensionCreate,
)
from app.modules.users.model import User
from app.shared.enums import StudentStatus, UserRole


class StudentSubscriptionService:
    """Сервис бизнес-логики абонементов учеников."""

    AUTOMATIC_EXTENSION_DAYS = 7

    @staticmethod
    def calculate_expiration_date(starts_on: date) -> date:
        """Вычисляет последний день действия абонемента сроком 30 дней."""

        return starts_on + timedelta(days=29)

    async def get_all(
        self,
        session: AsyncSession,
        current_user: User,
        branch_id: int | None = None,
        student_id: int | None = None,
        plan_id: int | None = None,
        active_on: date | None = None,
    ) -> list[StudentSubscription]:
        """Возвращает доступные пользователю абонементы."""

        if current_user.role == UserRole.BRANCH_ADMIN:
            branch_id = current_user.branch_id

        return await student_subscription_repository.get_all(
            session=session,
            branch_id=branch_id,
            student_id=student_id,
            plan_id=plan_id,
            active_on=active_on,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        subscription_id: int,
        current_user: User,
    ) -> StudentSubscription:
        """Возвращает абонемент с проверкой прав доступа."""

        subscription = await student_subscription_repository.get_by_id(
            session,
            subscription_id,
        )

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Абонемент ученика не найден",
            )

        ensure_branch_access(
            current_user,
            subscription.branch_id,
        )

        return subscription

    async def create(
        self,
        session: AsyncSession,
        data: StudentSubscriptionCreate,
        current_user: User,
    ) -> StudentSubscription:
        """Оформляет абонемент ученику."""

        student = await student_repository.get_by_id(
            session,
            data.student_id,
        )

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ученик не найден",
            )

        if student.status != StudentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Абонемент можно оформить только активному ученику",
            )

        ensure_branch_access(
            current_user,
            student.branch_id,
        )

        plan = await subscription_plan_repository.get_by_id(
            session,
            data.plan_id,
        )

        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип абонемента не найден",
            )

        if not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя оформить неактивный тип абонемента",
            )

        if plan.branch_id != student.branch_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Ученик и тип абонемента относятся " "к разным филиалам"),
            )

        expires_on = self.calculate_expiration_date(
            data.starts_on,
        )

        overlapping_subscription = await student_subscription_repository.find_overlapping(
            session=session,
            student_id=student.id,
            starts_on=data.starts_on,
            expires_on=expires_on,
        )

        if overlapping_subscription is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("У ученика уже есть абонемент, " "действующий в выбранный период"),
            )

        subscription = StudentSubscription(
            student_id=student.id,
            plan_id=plan.id,
            branch_id=student.branch_id,
            starts_on=data.starts_on,
            expires_on=expires_on,
            lessons_count=plan.lessons_count,
            price=plan.price,
            extension_days=0,
            comment=data.comment,
            created_by=current_user.id,
        )

        session.add(subscription)
        await session.commit()

        created_subscription = await student_subscription_repository.get_by_id(
            session,
            subscription.id,
        )

        if created_subscription is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить оформленный абонемент",
            )

        return created_subscription

    async def update(
        self,
        session: AsyncSession,
        subscription_id: int,
        data: StudentSubscriptionUpdate,
        current_user: User,
    ) -> StudentSubscription:
        """Обновляет дату начала или комментарий абонемента."""

        subscription = await self.get_by_id(
            session,
            subscription_id,
            current_user,
        )

        if data.starts_on is not None:
            new_expires_on = self.calculate_expiration_date(data.starts_on) + timedelta(
                days=subscription.extension_days
            )

            overlapping_subscription = await student_subscription_repository.find_overlapping(
                session=session,
                student_id=subscription.student_id,
                starts_on=data.starts_on,
                expires_on=new_expires_on,
                excluded_subscription_id=subscription.id,
            )

            if overlapping_subscription is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=("У ученика уже есть абонемент, " "действующий в выбранный период"),
                )

            subscription.starts_on = data.starts_on
            subscription.expires_on = new_expires_on

        if "comment" in data.model_fields_set:
            subscription.comment = data.comment

        await session.commit()

        updated_subscription = await student_subscription_repository.get_by_id(
            session,
            subscription.id,
        )

        if updated_subscription is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновлённый абонемент",
            )

        return updated_subscription

    async def extend(
        self,
        session: AsyncSession,
        subscription_id: int,
        data: SubscriptionExtensionCreate,
        current_user: User,
    ) -> StudentSubscription:
        """Продлевает срок действия абонемента."""

        subscription = await self.get_by_id(
            session,
            subscription_id,
            current_user,
        )

        new_expires_on = subscription.expires_on + timedelta(
            days=data.days,
        )

        overlapping_subscription = await student_subscription_repository.find_overlapping(
            session=session,
            student_id=subscription.student_id,
            starts_on=subscription.starts_on,
            expires_on=new_expires_on,
            excluded_subscription_id=subscription.id,
        )

        if overlapping_subscription is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Продление пересекается с другим " "абонементом ученика"),
            )

        subscription.expires_on = new_expires_on
        subscription.extension_days += data.days

        await session.commit()

        extended_subscription = await student_subscription_repository.get_by_id(
            session,
            subscription.id,
        )

        if extended_subscription is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить продлённый абонемент",
            )

        return extended_subscription

    async def extend_for_cancelled_lesson(
        self,
        session: AsyncSession,
        lesson: Lesson,
        current_user: User,
    ) -> int:
        """Продлевает абонементы из-за отмены занятия студией."""

        lesson_date = lesson.starts_at.astimezone(ZoneInfo("Europe/Moscow")).date()

        student_ids = await group_repository.get_active_student_ids(
            session=session,
            group_id=lesson.group_id,
        )

        extensions_count = 0

        for student_id in student_ids:
            subscription = await student_subscription_repository.get_valid_on_date(
                session=session,
                student_id=student_id,
                branch_id=lesson.group.branch_id,
                target_date=lesson_date,
            )

            if subscription is None:
                continue

            existing_extension = await student_subscription_repository.get_extension_by_lesson(
                session=session,
                subscription_id=subscription.id,
                lesson_id=lesson.id,
            )

            if existing_extension is not None:
                continue

            await self.apply_automatic_extension(
                session=session,
                subscription=subscription,
                lesson=lesson,
                current_user=current_user,
            )

            extensions_count += 1

        return extensions_count

    async def apply_automatic_extension(
        self,
        session: AsyncSession,
        subscription: StudentSubscription,
        lesson: Lesson,
        current_user: User,
    ) -> None:
        """Применяет автоматическое продление и сдвигает будущие абонементы."""

        days = self.AUTOMATIC_EXTENSION_DAYS
        previous_expires_on = subscription.expires_on

        following_subscriptions = await student_subscription_repository.get_following_subscriptions(
            session=session,
            student_id=subscription.student_id,
            after_date=previous_expires_on,
            excluded_subscription_id=subscription.id,
        )

        subscription.expires_on += timedelta(days=days)
        subscription.extension_days += days

        for following_subscription in following_subscriptions:
            following_subscription.starts_on += timedelta(days=days)
            following_subscription.expires_on += timedelta(days=days)

        extension = SubscriptionExtension(
            subscription_id=subscription.id,
            lesson_id=lesson.id,
            days=days,
            reason="Отмена занятия студией",
            created_by=current_user.id,
        )

        session.add(extension)


student_subscription_service = StudentSubscriptionService()
