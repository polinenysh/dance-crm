from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dance_styles.model import DanceStyle
from app.modules.dance_styles.schemas import (
    DanceStyleCreate,
    DanceStyleUpdate,
)
from app.shared.repository import BaseRepository


class DanceStyleRepository(
    BaseRepository[
        DanceStyle,
        DanceStyleCreate,
        DanceStyleUpdate,
    ]
):
    """Репозиторий для работы с танцевальными направлениями."""

    def __init__(self) -> None:
        """Инициализирует репозиторий направлений."""

        super().__init__(DanceStyle)

    async def get_all(
        self,
        session: AsyncSession,
        active_only: bool = False,
    ) -> list[DanceStyle]:
        """Возвращает список танцевальных направлений."""

        query = select(DanceStyle).order_by(DanceStyle.name)

        if active_only:
            query = query.where(DanceStyle.is_active.is_(True))

        result = await session.scalars(query)

        return list(result.all())

    async def get_by_name(
        self,
        session: AsyncSession,
        name: str,
    ) -> DanceStyle | None:
        """Возвращает направление по названию."""

        result = await session.scalars(
            select(DanceStyle).where(
                DanceStyle.name.ilike(name.strip()),
            )
        )

        return result.first()

    async def get_by_ids(
        self,
        session: AsyncSession,
        dance_style_ids: list[int],
    ) -> list[DanceStyle]:
        """Возвращает направления по списку идентификаторов."""

        if not dance_style_ids:
            return []

        result = await session.scalars(
            select(DanceStyle).where(
                DanceStyle.id.in_(dance_style_ids),
            )
        )

        return list(result.all())


dance_style_repository = DanceStyleRepository()
