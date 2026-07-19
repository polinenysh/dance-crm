from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.schedule.model import Lesson
    from app.modules.students.model import Student
    from app.modules.subscriptions.model import StudentSubscription
    from app.modules.users.model import User


class Attendance(IdMixin, TimestampMixin, Base):
    """Модель факта посещения учеником занятия."""

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint(
            "lesson_id",
            "student_id",
            name="uq_attendance_lesson_student",
        ),
        Index(
            "ix_attendance_student_id",
            "student_id",
        ),
        Index(
            "ix_attendance_subscription_id",
            "subscription_id",
        ),
    )

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey(
            "student_subscriptions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    marked_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    lesson: Mapped["Lesson"] = relationship(
        back_populates="attendances",
    )

    student: Mapped["Student"] = relationship(
        back_populates="attendances",
    )

    subscription: Mapped["StudentSubscription"] = relationship(
        back_populates="attendances",
    )

    marked_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[marked_by],
    )
