from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.halls.model import Hall
from app.modules.halls.schemas import HallCreate, HallUpdate
from app.shared.repository import BaseRepository


class HallRepository(
    BaseRepository[
        Hall,
        HallCreate,
        HallUpdate,
    ]
):
    """Репозиторий для работы с залами."""

    def __init__(self) -> None:
        """Инициализирует репозиторий залов."""

        super().__init__(Hall)

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
    ) -> list[Hall]:
        """Возвращает список залов с необязательной фильтрацией по филиалу."""

        query = select(Hall).order_by(Hall.name)

        if branch_id is not None:
            query = query.where(Hall.branch_id == branch_id)

        result = await session.scalars(query)
        return list(result.all())

    async def get_by_name_and_branch(
        self,
        session: AsyncSession,
        name: str,
        branch_id: int,
    ) -> Hall | None:
        """Возвращает зал по названию и филиалу."""

        result = await session.scalars(
            select(Hall).where(
                Hall.name == name,
                Hall.branch_id == branch_id,
            )
        )
        return result.first()


hall_repository = HallRepository()
