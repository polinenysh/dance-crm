from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep, OwnerDep
from app.modules.subscription_plans.schemas import (
    SubscriptionPlanCreate,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
)
from app.modules.subscription_plans.service import (
    subscription_plan_service,
)

router = APIRouter(
    prefix="/subscription-plans",
    tags=["Subscription plans"],
)


@router.get(
    "",
    response_model=list[SubscriptionPlanResponse],
)
async def get_subscription_plans(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    branch_id: int | None = Query(
        default=None,
        gt=0,
    ),
    active_only: bool = Query(
        default=False,
    ),
) -> list[SubscriptionPlanResponse]:
    """Возвращает список типов абонементов."""

    return await subscription_plan_service.get_all(
        session=session,
        current_user=current_user,
        branch_id=branch_id,
        active_only=active_only,
    )


@router.post(
    "",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription_plan(
    data: SubscriptionPlanCreate,
    session: SessionDep,
    current_user: OwnerDep,
) -> SubscriptionPlanResponse:
    """Создаёт тип абонемента."""

    return await subscription_plan_service.create(
        session,
        data,
        current_user,
    )


@router.get(
    "/{plan_id}",
    response_model=SubscriptionPlanResponse,
)
async def get_subscription_plan(
    plan_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> SubscriptionPlanResponse:
    """Возвращает тип абонемента по идентификатору."""

    return await subscription_plan_service.get_by_id(
        session,
        plan_id,
        current_user,
    )


@router.patch(
    "/{plan_id}",
    response_model=SubscriptionPlanResponse,
)
async def update_subscription_plan(
    plan_id: int,
    data: SubscriptionPlanUpdate,
    session: SessionDep,
    current_user: OwnerDep,
) -> SubscriptionPlanResponse:
    """Обновляет тип абонемента."""

    return await subscription_plan_service.update(
        session,
        plan_id,
        data,
        current_user,
    )
