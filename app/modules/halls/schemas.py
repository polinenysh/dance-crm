from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.schemas import ResponseSchema


class HallBase(BaseModel):
    """Общие поля зала."""

    branch_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0)


class HallUpdate(BaseModel):
    """Схема частичного обновления зала."""

    branch_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class HallCreate(HallBase):
    pass


class HallResponse(HallBase, ResponseSchema):
    """Схема ответа с данными зала."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class HallShortResponse(ResponseSchema):
    """Краткая информация о зале."""

    id: int
    name: str
    capacity: int
