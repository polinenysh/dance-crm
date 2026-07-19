from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.students.schemas import StudentShortResponse
from app.shared.schemas import ResponseSchema


class AttendanceSyncRequest(BaseModel):
    """Полный актуальный список присутствовавших учеников."""

    student_ids: list[int] = Field(default_factory=list)

    @field_validator("student_ids")
    @classmethod
    def validate_student_ids(cls, value: list[int]) -> list[int]:
        """Проверяет и удаляет повторяющиеся идентификаторы."""
        if any(student_id <= 0 for student_id in value):
            raise ValueError("Идентификаторы учеников должны быть положительными")
        return list(dict.fromkeys(value))


class AttendanceResponse(ResponseSchema):
    """Информация о посещении занятия."""

    id: int
    student: StudentShortResponse
    subscription_id: int
    marked_by: int | None
    created_at: datetime
    updated_at: datetime


class LessonAttendanceResponse(BaseModel):
    """Посещаемость конкретного занятия."""

    lesson_id: int
    students_count: int
    attendances: list[AttendanceResponse]