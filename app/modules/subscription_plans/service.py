from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import ensure_branch_access
from app.modules.branches.repository import branch_repository
from app.modules.subscription_plans.model import SubscriptionPlan
from app.modules.subscription_plans.repository import (
    subscription_plan_repository,
)
from app.modules.subscription_plans.schemas import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
)
from app.modules.users.model import User
from app.shared.enums import UserRole


class SubscriptionPlanService:
    """Сервис бизнес-логики типов абонементов."""

    async def get_all(
        self,
        session: AsyncSession,
        current_user: User,
        branch_id: int | None = None,
        active_only: bool = False,
    ) -> list[SubscriptionPlan]:
        """Возвращает доступные пользователю типы абонементов."""

        if current_user.role == UserRole.BRANCH_ADMIN:
            branch_id = current_user.branch_id

        return await subscription_plan_repository.get_all(
            session=session,
            branch_id=branch_id,
            active_only=active_only,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        plan_id: int,
        current_user: User,
    ) -> SubscriptionPlan:
        """Возвращает тип абонемента с проверкой доступа."""

        plan = await subscription_plan_repository.get_by_id(
            session,
            plan_id,
        )

        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип абонемента не найден",
            )

        ensure_branch_access(
            current_user,
            plan.branch_id,
        )

        return plan

    async def validate_branch(
        self,
        session: AsyncSession,
        branch_id: int,
    ) -> None:
        """Проверяет существование и активность филиала."""

        branch = await branch_repository.get_by_id(
            session,
            branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Филиал не найден",
            )

        if not branch.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Нельзя создать тип абонемента " "для неактивного филиала"),
            )

    async def create(
        self,
        session: AsyncSession,
        data: SubscriptionPlanCreate,
        current_user: User,
    ) -> SubscriptionPlan:
        """Создаёт тип абонемента."""

        ensure_branch_access(
            current_user,
            data.branch_id,
        )

        await self.validate_branch(
            session,
            data.branch_id,
        )

        normalized_name = data.name.strip().lower()

        existing_plan = await subscription_plan_repository.get_by_name_and_branch(
            session,
            normalized_name,
            data.branch_id,
        )

        if existing_plan is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Тип абонемента с таким названием " "уже существует в филиале"),
            )

        plan = SubscriptionPlan(
            branch_id=data.branch_id,
            name=normalized_name,
            lessons_count=data.lessons_count,
            price=data.price,
            is_active=True,
        )

        session.add(plan)
        await session.commit()

        created_plan = await subscription_plan_repository.get_by_id(
            session,
            plan.id,
        )

        if created_plan is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить созданный тип абонемента",
            )

        return created_plan

    async def update(
        self,
        session: AsyncSession,
        plan_id: int,
        data: SubscriptionPlanUpdate,
        current_user: User,
    ) -> SubscriptionPlan:
        """Обновляет тип абонемента."""

        plan = await self.get_by_id(
            session,
            plan_id,
            current_user,
        )

        target_branch_id = data.branch_id if data.branch_id is not None else plan.branch_id

        ensure_branch_access(
            current_user,
            target_branch_id,
        )

        if data.branch_id is not None:
            await self.validate_branch(
                session,
                target_branch_id,
            )

        normalized_name = data.name.strip().lower() if data.name is not None else plan.name

        if data.name is not None or data.branch_id is not None:
            existing_plan = await subscription_plan_repository.get_by_name_and_branch(
                session,
                normalized_name,
                target_branch_id,
            )

            if existing_plan is not None and existing_plan.id != plan.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=("Тип абонемента с таким названием " "уже существует в филиале"),
                )

        update_data = data.model_dump(
            exclude_unset=True,
            exclude={"name"},
        )

        for field, value in update_data.items():
            setattr(plan, field, value)

        if data.name is not None:
            plan.name = normalized_name

        await session.commit()

        updated_plan = await subscription_plan_repository.get_by_id(
            session,
            plan.id,
        )

        if updated_plan is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновлённый тип абонемента",
            )

        return updated_plan


subscription_plan_service = SubscriptionPlanService()
