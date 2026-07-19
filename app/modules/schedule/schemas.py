from datetime import date, datetime, time

from pydantic import BaseModel, Field, model_validator

from app.modules.groups.schemas import GroupShortResponse
from app.modules.halls.schemas import HallShortResponse
from app.modules.teachers.schemas import TeacherShortResponse
from app.shared.enums import LessonStatus, Weekday
from app.shared.schemas import ResponseSchema


class ScheduleSlotCreate(BaseModel):
    """Схема создания повторяющегося элемента расписания."""

    group_id: int = Field(gt=0)
    hall_id: int = Field(gt=0)
    weekday: Weekday
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleSlotCreate":
        """Проверяет время начала и окончания занятия."""

        if self.start_time >= self.end_time:
            raise ValueError("Время окончания должно быть позже времени начала")

        return self


class ScheduleSlotUpdate(BaseModel):
    """Схема частичного обновления элемента расписания."""

    hall_id: int | None = Field(default=None, gt=0)
    weekday: Weekday | None = None
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None


class ScheduleSlotResponse(ResponseSchema):
    """Схема ответа с элементом расписания."""

    id: int
    group: GroupShortResponse
    hall: HallShortResponse
    weekday: Weekday
    start_time: time
    end_time: time
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LessonGenerateRequest(BaseModel):
    """Схема генерации конкретных занятий."""

    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_date_range(self) -> "LessonGenerateRequest":
        """Проверяет диапазон генерации занятий."""

        if self.date_from > self.date_to:
            raise ValueError("Начальная дата не может быть позже конечной")

        if (self.date_to - self.date_from).days > 93:
            raise ValueError("За один запрос можно создать занятия максимум на 93 дня")

        return self


class LessonCancelRequest(BaseModel):
    """Схема отмены занятия."""

    reason: str = Field(
        min_length=1,
        max_length=500,
    )
    cancelled_by_studio: bool = True


class LessonRescheduleRequest(BaseModel):
    """Схема переноса занятия."""

    hall_id: int | None = Field(default=None, gt=0)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_datetime_range(
        self,
    ) -> "LessonRescheduleRequest":
        """Проверяет время перенесённого занятия."""

        if self.starts_at >= self.ends_at:
            raise ValueError("Окончание занятия должно быть позже начала")

        return self


class LessonResponse(ResponseSchema):
    """Схема ответа с конкретным занятием."""

    id: int
    schedule_slot_id: int | None
    group: GroupShortResponse
    hall: HallShortResponse
    teacher: TeacherShortResponse
    starts_at: datetime
    ends_at: datetime
    status: LessonStatus
    completed_at: datetime | None
    cancellation_reason: str | None
    cancelled_by_studio: bool
    created_at: datetime
    updated_at: datetime
