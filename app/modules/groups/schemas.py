from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.branches.schemas import BranchShortResponse
from app.modules.dance_styles.schemas import DanceStyleShortResponse
from app.modules.students.schemas import StudentShortResponse
from app.modules.teachers.schemas import TeacherShortResponse
from app.shared.schemas import ResponseSchema


class GroupCreate(BaseModel):
    """Схема создания учебной группы."""

    branch_id: int = Field(gt=0)
    dance_style_id: int = Field(gt=0)
    teacher_id: int = Field(gt=0)

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    max_students: int = Field(
        default=25,
        ge=1,
        le=25,
    )


class GroupUpdate(BaseModel):
    """Схема частичного обновления учебной группы."""

    branch_id: int | None = Field(
        default=None,
        gt=0,
    )
    dance_style_id: int | None = Field(
        default=None,
        gt=0,
    )
    teacher_id: int | None = Field(
        default=None,
        gt=0,
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    max_students: int | None = Field(
        default=None,
        ge=1,
        le=25,
    )
    is_active: bool | None = None


class GroupMembershipCreate(BaseModel):
    """Схема добавления ученика в группу."""

    student_id: int = Field(gt=0)


class GroupMemberResponse(ResponseSchema):
    """Информация об ученике в составе группы."""

    membership_id: int
    student: StudentShortResponse
    joined_at: datetime


class GroupShortResponse(ResponseSchema):
    """Краткая информация об учебной группе."""

    id: int
    name: str


class GroupResponse(ResponseSchema):
    """Полная информация об учебной группе."""

    id: int
    name: str
    max_students: int
    students_count: int
    is_active: bool

    branch: BranchShortResponse
    dance_style: DanceStyleShortResponse
    teacher: TeacherShortResponse
    students: list[GroupMemberResponse]

    created_at: datetime
    updated_at: datetime
