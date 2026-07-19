from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(
    Generic[
        ModelType,
        CreateSchemaType,
        UpdateSchemaType,
    ]
):
    """Базовый репозиторий с общими CRUD-операциями."""

    def __init__(self, model: type[ModelType]) -> None:
        """Инициализирует репозиторий для указанной SQLAlchemy-модели."""

        self.model = model

    async def get_all(
        self,
        session: AsyncSession,
    ) -> list[ModelType]:
        """Возвращает все записи модели."""

        result = await session.scalars(select(self.model))
        return list(result.all())

    async def get_by_id(
        self,
        session: AsyncSession,
        object_id: int,
    ) -> ModelType | None:
        """Возвращает запись по идентификатору."""

        return await session.get(self.model, object_id)

    async def create(
        self,
        session: AsyncSession,
        data: CreateSchemaType,
    ) -> ModelType:
        """Создаёт новую запись в базе данных."""

        instance = self.model(**data.model_dump())

        session.add(instance)
        await session.commit()
        await session.refresh(instance)

        return instance

    async def update(
        self,
        session: AsyncSession,
        instance: ModelType,
        data: UpdateSchemaType,
    ) -> ModelType:
        """Обновляет существующую запись."""

        update_data: dict[str, Any] = data.model_dump(
            exclude_unset=True,
        )

        for field, value in update_data.items():
            setattr(instance, field, value)

        await session.commit()
        await session.refresh(instance)

        return instance
