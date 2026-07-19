from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.subscription_plans.model import SubscriptionPlan


class SubscriptionPlanRepository:
    """Репозиторий для работы с типами абонементов."""

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
        active_only: bool = False,
    ) -> list[SubscriptionPlan]:
        """Возвращает типы абонементов с фильтрацией."""

        query: Select[tuple[SubscriptionPlan]] = select(SubscriptionPlan).options(
            selectinload(SubscriptionPlan.branch),
        )

        if branch_id is not None:
            query = query.where(
                SubscriptionPlan.branch_id == branch_id,
            )

        if active_only:
            query = query.where(
                SubscriptionPlan.is_active.is_(True),
            )

        query = query.order_by(
            SubscriptionPlan.lessons_count,
            SubscriptionPlan.price,
            SubscriptionPlan.name,
        )

        result = await session.scalars(query)

        return list(result.all())

    async def get_by_id(
        self,
        session: AsyncSession,
        plan_id: int,
    ) -> SubscriptionPlan | None:
        """Возвращает тип абонемента по идентификатору."""

        result = await session.scalars(
            select(SubscriptionPlan)
            .options(
                selectinload(SubscriptionPlan.branch),
            )
            .where(
                SubscriptionPlan.id == plan_id,
            )
            .execution_options(
                populate_existing=True,
            )
        )

        return result.first()

    async def get_by_name_and_branch(
        self,
        session: AsyncSession,
        name: str,
        branch_id: int,
    ) -> SubscriptionPlan | None:
        """Возвращает тип абонемента по названию и филиалу."""

        normalized_name = name.strip().lower()

        result = await session.scalars(
            select(SubscriptionPlan).where(
                SubscriptionPlan.branch_id == branch_id,
                SubscriptionPlan.name == normalized_name,
            )
        )

        return result.first()


subscription_plan_repository = SubscriptionPlanRepository()
