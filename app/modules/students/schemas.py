from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.branches.schemas import BranchShortResponse
from app.modules.parents.schemas import ParentShortResponse
from app.shared.enums import StudentStatus
from app.shared.schemas import ResponseSchema


class StudentBase(BaseModel):
    """Общие собственные поля ученика."""

    first_name: str = Field(
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
    )
    birth_date: date | None = None
    comment: str | None = None

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(
        cls,
        value: date | None,
    ) -> date | None:
        """Проверяет, что дата рождения не находится в будущем."""

        if value is not None and value > date.today():
            raise ValueError(
                "Дата рождения не может находиться в будущем"
            )

        return value


class StudentCreate(StudentBase):
    """Схема создания ученика."""

    parent_id: int = Field(gt=0)
    branch_id: int = Field(gt=0)


class StudentUpdate(BaseModel):
    """Схема частичного обновления ученика."""

    parent_id: int | None = Field(default=None, gt=0)
    branch_id: int | None = Field(default=None, gt=0)
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
    birth_date: date | None = None
    status: StudentStatus | None = None
    comment: str | None = None

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(
        cls,
        value: date | None,
    ) -> date | None:
        """Проверяет дату рождения при обновлении ученика."""

        if value is not None and value > date.today():
            raise ValueError(
                "Дата рождения не может находиться в будущем"
            )

        return value


class StudentResponse(StudentBase, ResponseSchema):
    """Полная информация об ученике со связанными сущностями."""

    id: int
    status: StudentStatus
    parent: ParentShortResponse
    branch: BranchShortResponse
    created_at: datetime
    updated_at: datetime


class StudentArchiveRequest(BaseModel):
    """Схема архивирования ученика."""

    comment: str | None = None


class StudentShortResponse(ResponseSchema):
    """Краткая информация об ученике."""

    id: int
    first_name: str
    last_name: str
    birth_date: date | None
    status: StudentStatus