from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.schemas import ResponseSchema


class ParentBase(BaseModel):
    """Общие поля родителя."""

    first_name: str = Field(
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
    )
    phone: str = Field(
        min_length=12,
        max_length=12,
    )
    comment: str | None = None


class ParentCreate(ParentBase):
    """Схема создания родителя."""


class ParentUpdate(BaseModel):
    """Схема частичного обновления родителя."""

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    phone: str | None = Field(
        default=None,
        min_length=12,
        max_length=12,
    )
    comment: str | None = None


class ParentShortResponse(ResponseSchema):
    """Краткая информация о родителе для вложенных ответов."""

    id: int
    first_name: str
    last_name: str
    phone: str


class ParentResponse(ParentBase, ResponseSchema):
    """Полная информация о родителе."""

    id: int
    created_at: datetime
    updated_at: datetime