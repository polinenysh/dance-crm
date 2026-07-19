from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.shared.enums import UserRole

if TYPE_CHECKING:
    from app.modules.branches.model import Branch
    from app.modules.payments.model import Payment


class User(IdMixin, TimestampMixin, Base):
    """Модель учётной записи сотрудника CRM."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(12),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
    )

    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    branch: Mapped["Branch | None"] = relationship(
        back_populates="users",
    )


    created_payments: Mapped[list["Payment"]] = relationship(
        foreign_keys="Payment.created_by",
        back_populates="creator",
    )

    cancelled_payments: Mapped[list["Payment"]] = relationship(
        foreign_keys="Payment.cancelled_by",
        back_populates="canceller",
    )

    refunded_payments: Mapped[list["Payment"]] = relationship(
        foreign_keys="Payment.refunded_by",
        back_populates="refunder",
    )