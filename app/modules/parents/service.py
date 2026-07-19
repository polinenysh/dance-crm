from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.parents.model import Parent
from app.modules.parents.repository import parent_repository
from app.modules.parents.schemas import ParentCreate, ParentUpdate
from app.modules.users.model import User
from app.shared.enums import UserRole


class ParentService:
    """Сервис бизнес-логики родителей."""

    async def get_all(
        self,
        session: AsyncSession,
        current_user: User,
        search: str | None = None,
    ) -> list[Parent]:
        """Возвращает доступный сотруднику список родителей."""

        branch_id = None

        if current_user.role == UserRole.BRANCH_ADMIN:
            branch_id = current_user.branch_id

        return await parent_repository.get_all(
            session,
            branch_id=branch_id,
            search=search,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        parent_id: int,
        current_user: User,
    ) -> Parent:
        """Возвращает родителя с проверкой доступа."""

        parent = await parent_repository.get_by_id(
            session,
            parent_id,
        )

        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Родитель не найден",
            )

        if current_user.role == UserRole.BRANCH_ADMIN:
            if current_user.branch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Администратору не назначен филиал",
                )

            has_access = (
                await parent_repository.has_student_in_branch(
                    session,
                    parent.id,
                    current_user.branch_id,
                )
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к этому родителю",
                )

        return parent

    async def create(
        self,
        session: AsyncSession,
        data: ParentCreate,
    ) -> Parent:
        """Создаёт карточку родителя."""

        existing_parent = await parent_repository.get_by_phone(
            session,
            data.phone,
        )

        if existing_parent is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Родитель с таким телефоном уже существует",
            )

        return await parent_repository.create(
            session,
            data,
        )

    async def update(
        self,
        session: AsyncSession,
        parent_id: int,
        data: ParentUpdate,
        current_user: User,
    ) -> Parent:
        """Обновляет карточку родителя."""

        parent = await self.get_by_id(
            session,
            parent_id,
            current_user,
        )

        if data.phone is not None and data.phone != parent.phone:
            existing_parent = await parent_repository.get_by_phone(
                session,
                data.phone,
            )

            if existing_parent is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Родитель с таким телефоном уже существует",
                )

        return await parent_repository.update(
            session,
            parent,
            data,
        )


parent_service = ParentService()