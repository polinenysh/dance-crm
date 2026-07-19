from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.branches.schemas import BranchShortResponse
from app.modules.students.schemas import StudentShortResponse
from app.modules.subscription_plans.schemas import (
    SubscriptionPlanShortResponse,
)
from app.shared.enums import SubscriptionStatus
from app.shared.schemas import ResponseSchema


class StudentSubscriptionCreate(BaseModel):
    """Схема оформления абонемента ученику."""

    student_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    starts_on: date
    comment: str | None = Field(
        default=None,
        max_length=500,
    )


class StudentSubscriptionUpdate(BaseModel):
    """Схема изменения данных абонемента."""

    starts_on: date | None = None
    comment: str | None = Field(
        default=None,
        max_length=500,
    )


class SubscriptionExtensionCreate(BaseModel):
    """Схема продления абонемента."""

    days: int = Field(
        default=7,
        gt=0,
    )


class StudentSubscriptionShortResponse(ResponseSchema):
    """Краткая информация об абонементе ученика."""

    id: int
    starts_on: date
    expires_on: date
    lessons_count: int
    price: int
    status: SubscriptionStatus


class StudentSubscriptionResponse(ResponseSchema):
    """Полная информация об абонементе ученика."""

    id: int

    student: StudentShortResponse
    plan: SubscriptionPlanShortResponse
    branch: BranchShortResponse

    starts_on: date
    expires_on: date

    lessons_count: int
    lessons_used: int
    lessons_remaining: int

    price: int
    extension_days: int

    status: SubscriptionStatus
    comment: str | None

    created_at: datetime
    updated_at: datetime