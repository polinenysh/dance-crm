from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.modules.payments.enums import PaymentMethod, PaymentStatus

if TYPE_CHECKING:
    from app.modules.branches.model import Branch
    from app.modules.students.model import Student
    from app.modules.subscriptions.model import StudentSubscription
    from app.modules.users.model import User


class Payment(Base, TimestampMixin):
    """Оплата ученика."""

    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_payments_amount_positive",
        ),
        Index(
            "ix_payments_student_paid_at",
            "student_id",
            "paid_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "student_subscriptions.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(
            PaymentMethod,
            name="payment_method",
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
        default=PaymentStatus.COMPLETED,
        server_default=PaymentStatus.COMPLETED.value,
    )

    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refunded_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    refund_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    student: Mapped["Student"] = relationship(
        back_populates="payments",
    )

    branch: Mapped["Branch"] = relationship(
        back_populates="payments",
    )

    subscription: Mapped["StudentSubscription | None"] = relationship(
        back_populates="payments",
    )

    creator: Mapped["User"] = relationship(
        foreign_keys=[created_by],
        back_populates="created_payments",
    )

    canceller: Mapped["User | None"] = relationship(
        foreign_keys=[cancelled_by],
        back_populates="cancelled_payments",
    )

    refunder: Mapped["User | None"] = relationship(
        foreign_keys=[refunded_by],
        back_populates="refunded_payments",
    )