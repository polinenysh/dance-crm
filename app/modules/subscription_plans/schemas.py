from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.branches.schemas import BranchShortResponse
from app.shared.schemas import ResponseSchema


class SubscriptionPlanCreate(BaseModel):
    """Схема создания типа абонемента."""

    branch_id: int = Field(gt=0)

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    lessons_count: int = Field(gt=0)

    price: int = Field(ge=0)


class SubscriptionPlanUpdate(BaseModel):
    """Схема частичного обновления типа абонемента."""

    branch_id: int | None = Field(
        default=None,
        gt=0,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    lessons_count: int | None = Field(
        default=None,
        gt=0,
    )

    price: int | None = Field(
        default=None,
        ge=0,
    )

    is_active: bool | None = None


class SubscriptionPlanShortResponse(ResponseSchema):
    """Краткая информация о типе абонемента."""

    id: int
    name: str
    lessons_count: int
    price: int


class SubscriptionPlanResponse(ResponseSchema):
    """Полная информация о типе абонемента."""

    id: int
    name: str
    lessons_count: int
    price: int
    is_active: bool
    branch: BranchShortResponse
    created_at: datetime
    updated_at: datetime
