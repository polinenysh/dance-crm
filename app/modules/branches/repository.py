from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.branches.schemas import (
    BranchCreate,
    BranchUpdate,
)
from app.shared.repository import BaseRepository


class BranchRepository(
    BaseRepository[
        Branch,
        BranchCreate,
        BranchUpdate,
    ]
):
    """Репозиторий для работы с филиалами."""

    def __init__(self) -> None:
        """Инициализирует репозиторий филиалов."""

        super().__init__(Branch)

    async def get_all(
        self,
        session: AsyncSession,
    ) -> list[Branch]:
        """Возвращает филиалы, отсортированные по названию."""

        result = await session.scalars(select(Branch).order_by(Branch.name))
        return list(result.all())

    async def get_by_name(
        self,
        session: AsyncSession,
        name: str,
    ) -> Branch | None:
        """Возвращает филиал по названию."""

        result = await session.scalars(select(Branch).where(Branch.name == name))
        return result.first()


branch_repository = BranchRepository()
