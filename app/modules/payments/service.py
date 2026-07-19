from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.payments.enums import PaymentStatus
from app.modules.payments.model import Payment
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schemas import (
    PaymentCreate,
    PaymentListResponse,
    PaymentRefund,
    PaymentResponse,
    PaymentSummaryResponse,
    PaymentUpdate,
)
from app.modules.students.model import Student
from app.modules.subscriptions.model import StudentSubscription
from app.modules.users.model import User
from app.shared.enums import UserRole


class PaymentService:
    """Сервис управления оплатами."""

    def __init__(
        self,
        session: AsyncSession,
        repository: PaymentRepository,
    ) -> None:
        """Инициализирует сервис."""

        self.session = session
        self.repository = repository

    async def create(
        self,
        data: PaymentCreate,
        current_user: User,
    ) -> Payment:
        """Регистрирует новую оплату."""

        await self._check_branch_access(
            current_user=current_user,
            branch_id=data.branch_id,
        )

        student = await self.session.get(
            Student,
            data.student_id,
        )

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ученик не найден",
            )

        if student.branch_id != data.branch_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ученик относится к другому филиалу",
            )

        await self._validate_subscription(
            subscription_id=data.subscription_id,
            student_id=data.student_id,
            branch_id=data.branch_id,
        )

        paid_at = data.paid_at or datetime.now(UTC)

        payment = await self.repository.create(
            data=data,
            created_by=current_user.id,
            paid_at=paid_at,
        )

        await self.session.commit()
        await self.session.refresh(payment)

        return payment

    async def get(
        self,
        payment_id: int,
        current_user: User,
    ) -> Payment:
        """Возвращает оплату."""

        payment = await self._get_payment_or_404(
            payment_id=payment_id,
        )

        await self._check_branch_access(
            current_user=current_user,
            branch_id=payment.branch_id,
        )

        return payment

    async def list(
        self,
        current_user: User,
        *,
        branch_id: int | None = None,
        student_id: int | None = None,
        subscription_id: int | None = None,
        payment_status: PaymentStatus | None = None,
        paid_from: datetime | None = None,
        paid_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaymentListResponse:
        """Возвращает доступный пользователю список оплат."""

        effective_branch_id = await self._resolve_branch_filter(
            current_user=current_user,
            branch_id=branch_id,
        )

        payments = await self.repository.list(
            branch_id=effective_branch_id,
            student_id=student_id,
            subscription_id=subscription_id,
            status=payment_status,
            paid_from=paid_from,
            paid_to=paid_to,
            limit=limit,
            offset=offset,
        )

        total = await self.repository.count(
            branch_id=effective_branch_id,
            student_id=student_id,
            subscription_id=subscription_id,
            status=payment_status,
            paid_from=paid_from,
            paid_to=paid_to,
        )

        return PaymentListResponse(
            items=[
                PaymentResponse.model_validate(payment)
                for payment in payments
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update(
        self,
        payment_id: int,
        data: PaymentUpdate,
        current_user: User,
    ) -> Payment:
        """Изменяет реквизиты проведённой оплаты."""

        payment = await self._get_payment_or_404(
            payment_id=payment_id,
            for_update=True,
        )

        await self._check_branch_access(
            current_user=current_user,
            branch_id=payment.branch_id,
        )

        if payment.status != PaymentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Можно изменять только проведённую оплату"
                ),
            )

        payment = await self.repository.update(
            payment=payment,
            data=data,
        )

        await self.session.commit()
        await self.session.refresh(payment)

        return payment

    async def cancel(
        self,
        payment_id: int,
        reason: str,
        current_user: User,
    ) -> Payment:
        """Отменяет ошибочно зарегистрированную оплату."""

        payment = await self._get_payment_or_404(
            payment_id=payment_id,
            for_update=True,
        )

        await self._check_branch_access(
            current_user=current_user,
            branch_id=payment.branch_id,
        )

        if payment.status == PaymentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Оплата уже отменена",
            )

        if payment.status == PaymentStatus.REFUNDED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Возвращённую оплату нельзя отменить",
            )

        payment.status = PaymentStatus.CANCELLED
        payment.cancelled_at = datetime.now(UTC)
        payment.cancelled_by = current_user.id
        payment.cancellation_reason = reason

        await self.session.commit()
        await self.session.refresh(payment)

        return payment

    async def refund(
        self,
        payment_id: int,
        data: PaymentRefund,
        current_user: User,
    ) -> Payment:
        """Отмечает оплату как возвращённую."""

        payment = await self._get_payment_or_404(
            payment_id=payment_id,
            for_update=True,
        )

        await self._check_branch_access(
            current_user=current_user,
            branch_id=payment.branch_id,
        )

        if payment.status == PaymentStatus.REFUNDED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Оплата уже возвращена",
            )

        if payment.status == PaymentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Отменённую оплату нельзя вернуть",
            )

        payment.status = PaymentStatus.REFUNDED
        payment.refunded_at = datetime.now(UTC)
        payment.refunded_by = current_user.id
        payment.refund_reason = data.reason

        await self.session.commit()
        await self.session.refresh(payment)

        return payment

    async def get_summary(
        self,
        current_user: User,
        *,
        branch_id: int | None = None,
        paid_from: datetime | None = None,
        paid_to: datetime | None = None,
    ) -> PaymentSummaryResponse:
        """Возвращает сводку по оплатам."""

        effective_branch_id = await self._resolve_branch_filter(
            current_user=current_user,
            branch_id=branch_id,
        )

        rows = await self.repository.get_summary(
            branch_id=effective_branch_id,
            paid_from=paid_from,
            paid_to=paid_to,
        )

        amounts = {
            PaymentStatus.COMPLETED: 0,
            PaymentStatus.CANCELLED: 0,
            PaymentStatus.REFUNDED: 0,
        }

        counts = {
            PaymentStatus.COMPLETED: 0,
            PaymentStatus.CANCELLED: 0,
            PaymentStatus.REFUNDED: 0,
        }

        for payment_status, amount, count in rows:
            amounts[payment_status] = amount
            counts[payment_status] = count

        return PaymentSummaryResponse(
            completed_amount=amounts[PaymentStatus.COMPLETED],
            refunded_amount=amounts[PaymentStatus.REFUNDED],
            cancelled_amount=amounts[PaymentStatus.CANCELLED],
            completed_count=counts[PaymentStatus.COMPLETED],
            refunded_count=counts[PaymentStatus.REFUNDED],
            cancelled_count=counts[PaymentStatus.CANCELLED],
        )

    async def _get_payment_or_404(
        self,
        payment_id: int,
        *,
        for_update: bool = False,
    ) -> Payment:
        """Возвращает оплату или поднимает ошибку 404."""

        payment = await self.repository.get_by_id(
            payment_id=payment_id,
            for_update=for_update,
        )

        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оплата не найдена",
            )

        return payment

    async def _validate_subscription(
        self,
        subscription_id: int | None,
        student_id: int,
        branch_id: int,
    ) -> None:
        """Проверяет принадлежность абонемента."""

        if subscription_id is None:
            return

        subscription = await self.session.get(
            StudentSubscription,
            subscription_id,
        )

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Абонемент не найден",
            )

        if subscription.student_id != student_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Абонемент принадлежит другому ученику",
            )

        if subscription.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Абонемент относится к другому филиалу",
            )

    async def _check_branch_access(
        self,
        current_user: User,
        branch_id: int,
    ) -> None:
        """Проверяет доступ пользователя к филиалу."""

        if current_user.role == UserRole.OWNER:
            branch = await self.session.get(
                Branch,
                branch_id,
            )

            if branch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Филиал не найден",
                )

            return

        if current_user.role == UserRole.BRANCH_ADMIN:
            if current_user.branch_id != branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к этому филиалу",
                )

            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для работы с оплатами",
        )

    async def _resolve_branch_filter(
        self,
        current_user: User,
        branch_id: int | None,
    ) -> int | None:
        """Определяет фильтр филиала с учётом роли."""

        if current_user.role == UserRole.OWNER:
            if branch_id is not None:
                await self._check_branch_access(
                    current_user=current_user,
                    branch_id=branch_id,
                )

            return branch_id

        if current_user.role == UserRole.BRANCH_ADMIN:
            if current_user.branch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Администратор не привязан к филиалу",
                )

            if (
                branch_id is not None
                and branch_id != current_user.branch_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к этому филиалу",
                )

            return current_user.branch_id

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра оплат",
        )