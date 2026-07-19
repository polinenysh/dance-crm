from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.payments.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    """Данные для регистрации оплаты."""

    student_id: int = Field(
        gt=0,
    )

    branch_id: int = Field(
        gt=0,
    )

    subscription_id: int | None = Field(
        default=None,
        gt=0,
    )

    amount: int = Field(
        gt=0,
    )

    payment_method: PaymentMethod

    paid_at: datetime | None = None

    comment: str | None = Field(
        default=None,
        max_length=500,
    )


class PaymentUpdate(BaseModel):
    """Данные для изменения проведённой оплаты."""

    payment_method: PaymentMethod | None = None

    paid_at: datetime | None = None

    comment: str | None = Field(
        default=None,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "PaymentUpdate":
        """Проверяет наличие хотя бы одного изменяемого поля."""

        if not self.model_fields_set:
            raise ValueError("Необходимо передать хотя бы одно поле для изменения")

        return self


class PaymentCancel(BaseModel):
    """Данные для отмены оплаты."""

    reason: str = Field(
        min_length=1,
        max_length=500,
    )


class PaymentRefund(BaseModel):
    """Данные для возврата оплаты."""

    reason: str = Field(
        min_length=1,
        max_length=500,
    )


class PaymentResponse(BaseModel):
    """Информация об оплате."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    student_id: int
    branch_id: int
    subscription_id: int | None
    amount: int
    payment_method: PaymentMethod
    status: PaymentStatus
    paid_at: datetime
    comment: str | None
    created_by: int
    cancelled_at: datetime | None
    cancelled_by: int | None
    cancellation_reason: str | None
    refunded_at: datetime | None
    refunded_by: int | None
    refund_reason: str | None
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    """Список оплат с пагинацией."""

    items: list[PaymentResponse]
    total: int
    limit: int
    offset: int


class PaymentSummaryResponse(BaseModel):
    """Сводная информация по оплатам."""

    completed_amount: int
    refunded_amount: int
    cancelled_amount: int
    completed_count: int
    refunded_count: int
    cancelled_count: int
