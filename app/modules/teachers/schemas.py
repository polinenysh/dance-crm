from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.modules.dance_styles.schemas import DanceStyleShortResponse
from app.shared.schemas import ResponseSchema


class TeacherCreate(BaseModel):
    """Схема создания преподавателя."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=12)
    email: EmailStr | None = None
    dance_style_ids: list[int] = Field(default_factory=list)


class TeacherUpdate(BaseModel):
    """Схема обновления преподавателя."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=12)
    email: EmailStr | None = None
    dance_style_ids: list[int] | None = None
    is_active: bool | None = None


class TeacherResponse(ResponseSchema):
    """Схема ответа с данными преподавателя."""

    id: int
    first_name: str
    last_name: str
    phone: str | None
    email: EmailStr | None
    dance_styles: list[DanceStyleShortResponse]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TeacherShortResponse(ResponseSchema):
    """Краткая информация о преподавателе."""

    id: int
    first_name: str
    last_name: str
