from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payments.enums import PaymentStatus
from app.modules.payments.model import Payment
from app.modules.payments.schemas import PaymentCreate, PaymentUpdate


class PaymentRepository:
    """Репозиторий оплат."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий."""

        self.session = session

    async def get_by_id(
        self,
        payment_id: int,
        *,
        for_update: bool = False,
    ) -> Payment | None:
        """Возвращает оплату по идентификатору."""

        query = select(Payment).where(
            Payment.id == payment_id,
        )

        if for_update:
            query = query.with_for_update()

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def create(
        self,
        data: PaymentCreate,
        *,
        created_by: int,
        paid_at: datetime,
    ) -> Payment:
        """Создаёт оплату."""

        payment = Payment(
            student_id=data.student_id,
            branch_id=data.branch_id,
            subscription_id=data.subscription_id,
            amount=data.amount,
            payment_method=data.payment_method,
            status=PaymentStatus.COMPLETED,
            paid_at=paid_at,
            comment=data.comment,
            created_by=created_by,
        )

        self.session.add(payment)
        await self.session.flush()

        return payment

    async def update(
        self,
        payment: Payment,
        data: PaymentUpdate,
    ) -> Payment:
        """Изменяет оплату."""

        update_data = data.model_dump(
            exclude_unset=True,
        )

        for field, value in update_data.items():
            setattr(payment, field, value)

        await self.session.flush()

        return payment

    async def list(
        self,
        *,
        branch_id: int | None = None,
        student_id: int | None = None,
        subscription_id: int | None = None,
        status: PaymentStatus | None = None,
        paid_from: datetime | None = None,
        paid_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Payment]:
        """Возвращает список оплат."""

        query = self._apply_filters(
            select(Payment),
            branch_id=branch_id,
            student_id=student_id,
            subscription_id=subscription_id,
            status=status,
            paid_from=paid_from,
            paid_to=paid_to,
        )

        query = query.order_by(
            Payment.paid_at.desc(),
            Payment.id.desc(),
        ).limit(limit).offset(offset)

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def count(
        self,
        *,
        branch_id: int | None = None,
        student_id: int | None = None,
        subscription_id: int | None = None,
        status: PaymentStatus | None = None,
        paid_from: datetime | None = None,
        paid_to: datetime | None = None,
    ) -> int:
        """Возвращает количество оплат."""

        query = self._apply_filters(
            select(func.count(Payment.id)),
            branch_id=branch_id,
            student_id=student_id,
            subscription_id=subscription_id,
            status=status,
            paid_from=paid_from,
            paid_to=paid_to,
        )

        count = await self.session.scalar(query)

        return count or 0

    async def get_summary(
        self,
        *,
        branch_id: int | None = None,
        paid_from: datetime | None = None,
        paid_to: datetime | None = None,
    ) -> list[tuple[PaymentStatus, int, int]]:
        """Возвращает суммы и количество оплат по статусам."""

        query = select(
            Payment.status,
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(Payment.id),
        ).group_by(
            Payment.status,
        )

        query = self._apply_filters(
            query,
            branch_id=branch_id,
            paid_from=paid_from,
            paid_to=paid_to,
        )

        result = await self.session.execute(query)

        return list(result.tuples().all())

    @staticmethod
    def _apply_filters(
        query: Select,
        *,
        branch_id: int | None = None,
        student_id: int | None = None,
        subscription_id: int | None = None,
        status: PaymentStatus | None = None,
        paid_from: datetime | None = None,
        paid_to: datetime | None = None,
    ) -> Select:
        """Добавляет фильтры к запросу."""

        if branch_id is not None:
            query = query.where(
                Payment.branch_id == branch_id,
            )

        if student_id is not None:
            query = query.where(
                Payment.student_id == student_id,
            )

        if subscription_id is not None:
            query = query.where(
                Payment.subscription_id == subscription_id,
            )

        if status is not None:
            query = query.where(
                Payment.status == status,
            )

        if paid_from is not None:
            query = query.where(
                Payment.paid_at >= paid_from,
            )

        if paid_to is not None:
            query = query.where(
                Payment.paid_at <= paid_to,
            )

        return query