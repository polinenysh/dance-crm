from datetime import date

from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep
from app.modules.subscriptions.schemas import (
    StudentSubscriptionCreate,
    StudentSubscriptionResponse,
    StudentSubscriptionUpdate,
    SubscriptionExtensionCreate,
)
from app.modules.subscriptions.service import (
    student_subscription_service,
)

router = APIRouter(
    prefix="/subscriptions",
    tags=["Student subscriptions"],
)


@router.get(
    "",
    response_model=list[StudentSubscriptionResponse],
)
async def get_student_subscriptions(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    branch_id: int | None = Query(
        default=None,
        gt=0,
    ),
    student_id: int | None = Query(
        default=None,
        gt=0,
    ),
    plan_id: int | None = Query(
        default=None,
        gt=0,
    ),
    active_on: date | None = Query(
        default=None,
    ),
) -> list[StudentSubscriptionResponse]:
    """Возвращает абонементы учеников."""

    return await student_subscription_service.get_all(
        session=session,
        current_user=current_user,
        branch_id=branch_id,
        student_id=student_id,
        plan_id=plan_id,
        active_on=active_on,
    )


@router.post(
    "",
    response_model=StudentSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student_subscription(
    data: StudentSubscriptionCreate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentSubscriptionResponse:
    """Оформляет абонемент ученику."""

    return await student_subscription_service.create(
        session,
        data,
        current_user,
    )


@router.get(
    "/{subscription_id}",
    response_model=StudentSubscriptionResponse,
)
async def get_student_subscription(
    subscription_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentSubscriptionResponse:
    """Возвращает абонемент ученика."""

    return await student_subscription_service.get_by_id(
        session,
        subscription_id,
        current_user,
    )


@router.patch(
    "/{subscription_id}",
    response_model=StudentSubscriptionResponse,
)
async def update_student_subscription(
    subscription_id: int,
    data: StudentSubscriptionUpdate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentSubscriptionResponse:
    """Обновляет абонемент ученика."""

    return await student_subscription_service.update(
        session,
        subscription_id,
        data,
        current_user,
    )


@router.post(
    "/{subscription_id}/extend",
    response_model=StudentSubscriptionResponse,
)
async def extend_student_subscription(
    subscription_id: int,
    data: SubscriptionExtensionCreate,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> StudentSubscriptionResponse:
    """Продлевает абонемент ученика."""

    return await student_subscription_service.extend(
        session,
        subscription_id,
        data,
        current_user,
    )