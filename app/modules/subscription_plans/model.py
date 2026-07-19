from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.branches.model import Branch
    from app.modules.subscriptions.model import StudentSubscription


class SubscriptionPlan(IdMixin, TimestampMixin, Base):
    """Модель типа абонемента."""

    __tablename__ = "subscription_plans"
    __table_args__ = (
        CheckConstraint(
            "lessons_count > 0",
            name="ck_subscription_plans_lessons_count_positive",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_subscription_plans_price_non_negative",
        ),
        UniqueConstraint(
            "branch_id",
            "name",
            name="uq_subscription_plans_branch_name",
        ),
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    lessons_count: Mapped[int] = mapped_column(
        nullable=False,
    )

    price: Mapped[int] = mapped_column(
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    branch: Mapped["Branch"] = relationship(
        back_populates="subscription_plans",
    )

    subscriptions: Mapped[list["StudentSubscription"]] = relationship(
        back_populates="plan",
    )