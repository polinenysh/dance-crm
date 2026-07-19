from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import get_current_user
from app.modules.payments.dependencies import PaymentServiceDependency
from app.modules.payments.enums import PaymentStatus
from app.modules.payments.model import Payment
from app.modules.payments.schemas import (
    PaymentCancel,
    PaymentCreate,
    PaymentListResponse,
    PaymentRefund,
    PaymentResponse,
    PaymentSummaryResponse,
    PaymentUpdate,
)
from app.modules.users.model import User

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


CurrentUserDependency = Annotated[
    User,
    Depends(get_current_user),
]


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    data: PaymentCreate,
    current_user: CurrentUserDependency,
    service: PaymentServiceDependency,
) -> Payment:
    """Регистрирует оплату."""

    return await service.create(
        data=data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=PaymentListResponse,
)
async def list_payments(
    current_user: CurrentUserDependency,
    service: PaymentServiceDependency,
    branch_id: int | None = Query(
        default=None,
        gt=0,
    ),
    student_id: int | None = Query(
        default=None,
        gt=0,
    ),
    subscription_id: int | None = Query(
        default=None,
        gt=0,
    ),
    payment_status: PaymentStatus | None = Query(
        default=None,
        alias="status",
    ),
    paid_from: datetime | None = None,
    paid_to: datetime | None = None,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> PaymentListResponse:
    """Возвращает список оплат."""

    return await service.list(
        current_user=current_user,
        branch_id=branch_id,
        student_id=student_id,
        subscription_id=subscription_id,
        payment_status=payment_status,
        paid_from=paid_from,
        paid_to=paid_to,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/summary",
    response_model=PaymentSummaryResponse,
)
async def get_payments_summary(
    current_user: CurrentUserDependency,
    service: PaymentServiceDependency,
    branch_id: int | None = Query(
        default=None,
        gt=0,
    ),
    paid_from: datetime | None = None,
    paid_to: datetime | None = None,
) -> PaymentSummaryResponse:
    """Возвращает финансовую сводку."""

    return await service.get_summary(
        current_user=current_user,
        branch_id=branch_id,
        paid_from=paid_from,
        paid_to=paid_to,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
async def get_payment(
    payment_id: int,
    current_user: CurrentUserDependency,
    service: PaymentServiceDependency,
) -> Payment:
    """Возвращает оплату."""

    return await service.get(
        payment_id=payment_id,
        current_user=current_user,
    )


@router.patch(
    "/{payment_id}",
    response_model=PaymentResponse,
)
async def update_payment(
    payment_id: int,
    data: PaymentUpdate,
    current_user: CurrentUserDependency,
    service: PaymentServiceDependency,
) -> Payment:
    """Изменяет данные оплаты."""

    return await service.update(
        payment_id=payment_id,
        data=data,
        current_user=current_user,
    )


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
)
async def cancel_payment(
    payment_id: int,
    data: PaymentCancel,
    current_user: CurrentUserDependency,
    service: PaymentServiceDependency,
) -> Payment:
    """Отменяет ошибочно созданную оплату."""

    return await service.cancel(
        payment_id=payment_id,
        reason=data.reason,
        current_user=current_user,
    )


@router.post(
    "/{payment_id}/refund",
    response_model=PaymentResponse,
)
async def refund_payment(
    payment_id: int,
    data: PaymentRefund,
    current_user: CurrentUserDependency,
    service: PaymentServiceDependency,
) -> Payment:
    """Регистрирует возврат оплаты."""

    return await service.refund(
        payment_id=payment_id,
        data=data,
        current_user=current_user,
    )
