from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dance_styles.model import DanceStyle
from app.modules.dance_styles.repository import dance_style_repository
from app.modules.dance_styles.schemas import (
    DanceStyleCreate,
    DanceStyleUpdate,
)


class DanceStyleService:
    """Сервис бизнес-логики танцевальных направлений."""

    async def get_all(
        self,
        session: AsyncSession,
        active_only: bool = False,
    ) -> list[DanceStyle]:
        """Возвращает список направлений."""

        return await dance_style_repository.get_all(
            session,
            active_only,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        dance_style_id: int,
    ) -> DanceStyle:
        """Возвращает направление или ошибку 404."""

        dance_style = await dance_style_repository.get_by_id(
            session,
            dance_style_id,
        )

        if dance_style is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Направление не найдено",
            )

        return dance_style

    async def create(
        self,
        session: AsyncSession,
        data: DanceStyleCreate,
    ) -> DanceStyle:
        """Создаёт танцевальное направление."""

        existing_style = await dance_style_repository.get_by_name(
            session,
            data.name,
        )

        if existing_style is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Направление с таким названием уже существует",
            )

        return await dance_style_repository.create(
            session,
            data,
        )

    async def update(
        self,
        session: AsyncSession,
        dance_style_id: int,
        data: DanceStyleUpdate,
    ) -> DanceStyle:
        """Обновляет танцевальное направление."""

        dance_style = await self.get_by_id(
            session,
            dance_style_id,
        )

        if data.name is not None and data.name != dance_style.name:
            existing_style = await dance_style_repository.get_by_name(
                session,
                data.name,
            )

            if existing_style is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Направление с таким названием уже существует",
                )

        return await dance_style_repository.update(
            session,
            dance_style,
            data,
        )


dance_style_service = DanceStyleService()