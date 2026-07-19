from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.shared.enums import SubscriptionStatus

if TYPE_CHECKING:
    from app.modules.attendance.model import Attendance
    from app.modules.branches.model import Branch
    from app.modules.payments.model import Payment
    from app.modules.schedule.model import Lesson
    from app.modules.students.model import Student
    from app.modules.subscription_plans.model import SubscriptionPlan
    from app.modules.users.model import User


class StudentSubscription(IdMixin, TimestampMixin, Base):
    """Модель конкретного абонемента ученика."""

    __tablename__ = "student_subscriptions"
    __table_args__ = (
        CheckConstraint(
            "lessons_count > 0",
            name="ck_student_subscriptions_lessons_count_positive",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_student_subscriptions_price_non_negative",
        ),
        CheckConstraint(
            "expires_on >= starts_on",
            name="ck_student_subscriptions_date_range",
        ),
        CheckConstraint(
            "extension_days >= 0",
            name="ck_student_subscriptions_extension_days_non_negative",
        ),
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    plan_id: Mapped[int] = mapped_column(
        ForeignKey(
            "subscription_plans.id",
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
        index=True,
    )

    starts_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    expires_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    lessons_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    extension_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    student: Mapped["Student"] = relationship(
        back_populates="subscriptions",
    )

    plan: Mapped["SubscriptionPlan"] = relationship(
        back_populates="subscriptions",
    )

    branch: Mapped["Branch"] = relationship(
        back_populates="student_subscriptions",
    )

    created_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[created_by],
    )

    attendances: Mapped[list["Attendance"]] = relationship(
        back_populates="subscription",
    )

    extensions: Mapped[list["SubscriptionExtension"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="subscription",
    )

    @property
    def status(self) -> SubscriptionStatus:
        """Возвращает статус абонемента на текущую дату."""

        today = date.today()

        if today < self.starts_on:
            return SubscriptionStatus.UPCOMING

        if today > self.expires_on:
            return SubscriptionStatus.EXPIRED

        return SubscriptionStatus.ACTIVE

    @property
    def lessons_used(self) -> int:
        """Возвращает количество использованных занятий."""

        return len(self.attendances)

    @property
    def lessons_remaining(self) -> int:
        """Возвращает количество оставшихся занятий."""

        return self.lessons_count - self.lessons_used


class SubscriptionExtension(IdMixin, TimestampMixin, Base):
    """Модель продления абонемента."""

    __tablename__ = "subscription_extensions"
    __table_args__ = (
        CheckConstraint(
            "days > 0",
            name="ck_subscription_extensions_days_positive",
        ),
        UniqueConstraint(
            "subscription_id",
            "lesson_id",
            name="uq_subscription_extensions_subscription_lesson",
        ),
    )

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey(
            "student_subscriptions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "lessons.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    subscription: Mapped["StudentSubscription"] = relationship(
        back_populates="extensions",
    )

    lesson: Mapped["Lesson | None"] = relationship(
        back_populates="subscription_extensions",
    )

    created_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[created_by],
    )
