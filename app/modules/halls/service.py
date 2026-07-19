from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import ensure_branch_access
from app.modules.branches.repository import branch_repository
from app.modules.halls.model import Hall
from app.modules.halls.repository import hall_repository
from app.modules.halls.schemas import HallCreate, HallUpdate
from app.modules.users.model import User
from app.shared.enums import UserRole


class HallService:
    """Сервис бизнес-логики залов."""

    async def get_all(self, session: AsyncSession, current_user: User,
                      branch_id: int | None = None) -> list[Hall]:
        """Возвращает доступные сотруднику залы."""
        if current_user.role == UserRole.BRANCH_ADMIN:
            branch_id = current_user.branch_id
        elif branch_id is not None:
            await self._get_branch(session, branch_id)
        return await hall_repository.get_all(session, branch_id)

    async def _get_branch(self, session: AsyncSession, branch_id: int):
        """Возвращает филиал или ошибку 404."""
        branch = await branch_repository.get_by_id(session, branch_id)
        if branch is None:
            raise HTTPException(status_code=404, detail="Филиал не найден")
        return branch

    async def get_by_id(self, session: AsyncSession, hall_id: int,
                        current_user: User) -> Hall:
        """Возвращает зал с проверкой доступа."""
        hall = await hall_repository.get_by_id(session, hall_id)
        if hall is None:
            raise HTTPException(status_code=404, detail="Зал не найден")
        ensure_branch_access(current_user, hall.branch_id)
        return hall

    async def create(self, session: AsyncSession, data: HallCreate,
                     current_user: User) -> Hall:
        """Создаёт зал в доступном филиале."""
        ensure_branch_access(current_user, data.branch_id)
        branch = await self._get_branch(session, data.branch_id)
        if not branch.is_active:
            raise HTTPException(status_code=409, detail="Нельзя добавить зал в неактивный филиал")
        existing = await hall_repository.get_by_name_and_branch(session, data.name, data.branch_id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="В этом филиале уже есть зал с таким названием")
        return await hall_repository.create(session, data)

    async def update(self, session: AsyncSession, hall_id: int, data: HallUpdate,
                     current_user: User) -> Hall:
        """Обновляет зал с проверкой старого и нового филиала."""
        hall = await self.get_by_id(session, hall_id, current_user)
        target_branch_id = data.branch_id if data.branch_id is not None else hall.branch_id
        ensure_branch_access(current_user, target_branch_id)
        branch = await self._get_branch(session, target_branch_id)
        if not branch.is_active:
            raise HTTPException(status_code=409, detail="Нельзя перенести зал в неактивный филиал")
        target_name = data.name if data.name is not None else hall.name
        existing = await hall_repository.get_by_name_and_branch(session, target_name, target_branch_id)
        if existing is not None and existing.id != hall.id:
            raise HTTPException(status_code=409, detail="В этом филиале уже есть зал с таким названием")
        return await hall_repository.update(session, hall, data)


hall_service = HallService()
