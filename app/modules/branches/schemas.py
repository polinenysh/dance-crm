from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.schemas import ResponseSchema


class BranchBase(BaseModel):
    """Общие поля филиала."""

    name: str = Field(min_length=1, max_length=150)
    address: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=12)


class BranchCreate(BranchBase):
    """Схема создания филиала."""

    pass


class BranchUpdate(BaseModel):
    """Схема частичного обновления филиала."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=12)
    is_active: bool | None = None


class BranchShortResponse(ResponseSchema):
    """Краткая информация о филиале для вложенных ответов."""

    id: int
    name: str
    address: str


class BranchResponse(BranchBase, ResponseSchema):
    """Схема ответа с данными филиала."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
