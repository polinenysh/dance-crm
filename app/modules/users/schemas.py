from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.shared.enums import UserRole
from app.shared.schemas import ResponseSchema


class UserCreate(BaseModel):
    """Схема создания сотрудника."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=12)
    role: UserRole
    branch_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_branch(self) -> "UserCreate":
        """Проверяет соответствие роли и филиала."""

        if self.role == UserRole.BRANCH_ADMIN and self.branch_id is None:
            raise ValueError(
                "Для администратора необходимо указать филиал"
            )

        if self.role == UserRole.OWNER and self.branch_id is not None:
            raise ValueError(
                "Руководитель не должен быть привязан к филиалу"
            )

        return self


class UserUpdate(BaseModel):
    """Схема частичного обновления сотрудника."""

    email: EmailStr | None = None
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
    phone: str | None = Field(default=None, max_length=12)
    role: UserRole | None = None
    branch_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class UserResponse(ResponseSchema):
    """Схема ответа с данными сотрудника."""

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    role: UserRole
    branch_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserShortResponse(ResponseSchema):
    """Краткая информация о сотруднике."""

    id: int
    first_name: str
    last_name: str
    phone: str | None
    email: EmailStr