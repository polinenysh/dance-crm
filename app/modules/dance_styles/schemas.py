from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.schemas import ResponseSchema


class DanceStyleBase(BaseModel):
    """Общие поля танцевального направления."""

    name: str = Field(
        min_length=1,
        max_length=100,
    )
    description: str | None = None


class DanceStyleCreate(DanceStyleBase):
    """Схема создания танцевального направления."""
    pass


class DanceStyleUpdate(BaseModel):
    """Схема частичного обновления направления."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    description: str | None = None
    is_active: bool | None = None


class DanceStyleShortResponse(ResponseSchema):
    """Краткая информация о направлении."""

    id: int
    name: str


class DanceStyleResponse(DanceStyleBase, ResponseSchema):
    """Полная информация о танцевальном направлении."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime